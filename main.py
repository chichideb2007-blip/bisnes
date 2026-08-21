from flask import Flask, render_template, request, redirect, url_for, session, jsonify, make_response
from supabase import create_client
from collections import defaultdict
from datetime import datetime
from functools import wraps
import os
import time
import requests
import urllib.parse
import base64
import json
from google import genai 
from google.genai import types 

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fallback_dev_key")

# إعداد Supabase و Gemini
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- المعالج التلقائي للعملة ---
@app.context_processor
def inject_currency():
    company_code = session.get('company_code')
    if company_code:
        try:
            res = supabase.table('settings').select("currency").eq("company_code", company_code).single().execute()
            if res.data:
                return dict(currency=res.data.get('currency', ''))
        except:
            pass
    return dict(currency='DA')

# --- الدوال المساعدة ---

def get_product_from_db(product_id):
    res = supabase.table("inventory").select("*").eq("id", product_id).single().execute()
    return res.data if res.data else None

def get_wilayas_from_db():
    res = supabase.table("shipping_rates").select("*").order("id").execute()
    return res.data if res.data else []

def send_telegram_alert(product_name, company_name, company_code=""):
    try:
        if company_code:
            res_settings = supabase.table("settings").select("telegram_token, telegram_chat_id").eq("company_code", company_code).execute()
            if res_settings.data:
                s = res_settings.data[0]
                token, chat_id = s.get('telegram_token'), s.get('telegram_chat_id')
                if token and chat_id:
                    message = f"🚨 تنبيه نفاذ المخزون!\n\n🏪 المحل / المتجر: {company_name}\n📦 المنتج الذي نفد: {product_name}\n\n⚠️ لقد نفذت كمية هذا المنتج تماماً من المخزون!"
                    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={requests.utils.quote(message)}"
                    requests.get(url)
                    return
    except Exception as e:
        print("Telegram error:", e)

def send_telegram_alert_by_token(token, chat_id, message):
    if not token or not chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        params = {"chat_id": chat_id, "text": message}
        response = requests.get(url, params=params)
        return response.status_code == 200
    except Exception as e:
        return False

def send_order_alert(token, chat_id, message, order_id):
    if not token or not chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        keyboard = {
            "inline_keyboard": [[
                {"text": "✅ تم التحضير", "callback_data": f"status_done_{order_id}"},
                {"text": "❌ لم يتم التحضير", "callback_data": f"status_pending_{order_id}"}
            ]]
        }
        payload = {
            "chat_id": chat_id, 
            "text": message, 
            "reply_markup": keyboard
        }
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        return False

def get_products_by_shop_name(shop_name):
    try:
        shop_name_decoded = urllib.parse.unquote(shop_name).strip()
        settings = supabase.table("settings").select("company_code").ilike("company_name", shop_name_decoded).execute()
        if not settings.data:
            return []
        company_code = settings.data[0]['company_code']
        products = supabase.table("inventory").select("*").eq("company_id_text", company_code).execute()
        return products.data
    except Exception as e:
        return []

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'company_code' not in session: return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- المسارات ---

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/souhila')
def souhila_home():
    settings = {}
    try:
        settings_response = supabase.table('site_settings').select('*').execute()
        if settings_response.data:
            for item in settings_response.data:
                settings[item.get('key')] = item.get('value')
    except Exception as e:
        pass
    
    courses_res = supabase.table('souhila_courses').select('*').execute()
    courses = courses_res.data if courses_res.data else []
    
    return render_template('souhila.html', 
                           settings=settings,
                           courses=courses)

@app.route('/souhila-checkout/<int:course_id>')
def souhila_checkout(course_id):
    rates = get_wilayas_from_db() # أسعار الشحن الخاصة بولايات الجزائر
    
    # جلب الدورة المحددة بناءً على الـ ID القادم من الرابط
    course_res = supabase.table('souhila_courses').select('*').eq('id', course_id).single().execute()
    selected_course = course_res.data if course_res.data else None
    
    settings_res = supabase.table('site_settings').select('*').execute()
    settings = {item.get('key'): item.get('value') for item in settings_res.data} if settings_res.data else {}

    return render_template('souhila_checkout.html', rates=rates, course=selected_course, settings=settings)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    msg = None
    
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        try:
            if form_type == 'settings_update':
                phone = request.form.get('phone')
                whatsapp = request.form.get('whatsapp')
                email = request.form.get('email')
                map_url = request.form.get('map_url')
                telegram_token = request.form.get('telegram_token')
                telegram_chat_id = request.form.get('telegram_chat_id')
                
                supabase.table('site_settings').upsert([
                    {'key': 'phone', 'value': phone},
                    {'key': 'whatsapp', 'value': whatsapp},
                    {'key': 'email', 'value': email},
                    {'key': 'map_url', 'value': map_url},
                    {'key': 'telegram_token', 'value': telegram_token},
                    {'key': 'telegram_chat_id', 'value': telegram_chat_id}
                ], on_conflict='key').execute()
                
                msg = "تم حفظ التعديلات بنجاح!"

            elif form_type == 'add_course':
                title = request.form.get('course_title')
                desc = request.form.get('course_desc')
                price = request.form.get('course_price')
                image_file = request.files.get('course_image')
                
                image_url = ""
                if image_file and image_file.filename != '':
                    img_binary = image_file.read()
                    encoded_img = base64.b64encode(img_binary).decode('utf-8')
                    image_url = f"data:{image_file.content_type};base64,{encoded_img}"

                supabase.table('souhila_courses').insert({
                    'title': title,
                    'description': desc,
                    'price': price,
                    'image': image_url
                }).execute()
                
                msg = "Formation ajoutée avec succès !"

            elif form_type == 'delete_course':
                course_id = request.form.get('course_id')
                supabase.table('souhila_courses').delete().eq('id', course_id).execute()
                msg = "Formation supprimée avec succès !"
                
        except Exception as e:
            print(f"CRITICAL ERROR in admin POST: {e}")
            msg = f"Erreur de sauvegarde: {str(e)}"

    settings_response = supabase.table('site_settings').select('*').execute()
    settings = {}
    if settings_response.data:
        for item in settings_response.data:
            settings[item.get('key')] = item.get('value')

    courses_response = supabase.table('souhila_courses').select('*').execute()
    courses = courses_response.data if courses_response.data else []

    orders_response = supabase.table('orders_souhila').select('*').order('id', desc=True).execute()
    orders = orders_response.data if orders_response.data else []

    rates_res = supabase.table("shipping_rates").select("*").order("id").execute()
    rates = rates_res.data if rates_res.data else []

    return render_template('admin.html', settings=settings, courses=courses, orders=orders, rates=rates, msg=msg)

@app.route('/cart')
def cart_page():
    return render_template('cart.html')

@app.route('/checkout_cart')
def checkout_cart_page():
    rates = get_wilayas_from_db() 
    return render_template('checkout.html', rates=rates, is_cart=True)

@app.route('/checkout/<int:product_id>')
def checkout(product_id):
    rates = get_wilayas_from_db()
    jordan_res = supabase.table("jordan_rates").select("*").execute()
    jordan_rates = jordan_res.data if jordan_res.data else []
    product = get_product_from_db(product_id)
    
    if product:
        company_code = product.get('company_id_text')
        if company_code:
            settings_res = supabase.table("settings").select("company_name").eq("company_code", company_code).execute()
            if settings_res.data:
                session['current_shop_name'] = settings_res.data[0].get('company_name')
                
    return render_template('checkout.html', product=product, rates=rates, jordan_rates=jordan_rates)

@app.route('/submit-order', methods=['POST'])
@app.route('/submit-souhila-order', methods=['POST'])
def submit_order():
    customer_name = request.form.get('customer_name')
    customer_last_name = request.form.get('customer_last_name', '')
    full_name = f"{customer_name} {customer_last_name}".strip()
    
    phone = request.form.get('phone')
    country = request.form.get('country', 'algeria')
    
    baladiya = (
        request.form.get('baladiya') or 
        request.form.get('baladia') or 
        request.form.get('municipality') or 
        request.form.get('city') or 
        "غير محددة"
    )
    
    address = request.form.get('address', '')
    delivery_type = request.form.get('delivery_type')
    delivery_price = float(request.form.get('delivery_price', 0))
    quantity_ordered = int(request.form.get('quantity', 1))
    
    cart_raw = request.form.get('cart_data', '')
    cart_data = []
    
    if cart_raw and cart_raw != '[]':
        try:
            cart_data = json.loads(cart_raw)
        except:
            cart_data = []
            
    product_id = request.form.get('product_id')
    if not cart_data and product_id:
        single_product = get_product_from_db(product_id)
        if single_product:
            cart_data = [single_product]

    base_price = sum(float(item.get('price', 0)) * int(item.get('quantity', 1)) for item in cart_data)
    total_price = base_price + delivery_price

    company_code = ""
    if cart_data:
        first_item = cart_data[0]
        company_code = first_item.get('company_id_text') or first_item.get('company_code') or ""
    
    if not company_code and 'current_shop_name' in session:
        shop_name = session.get('current_shop_name')
        settings_res = supabase.table("settings").select("company_code").ilike("company_name", shop_name).execute()
        if settings_res.data:
            company_code = settings_res.data[0]['company_code']

    if not company_code and 'current_store2_name' in session:
        shop_name = session.get('current_store2_name')
        settings_res = supabase.table("settings").select("company_code").ilike("company_name", shop_name).execute()
        if settings_res.data:
            company_code = settings_res.data[0]['company_code']

    current_company = session.get('current_shop_name') or session.get('current_store2_name') or "متجر غير معروف"
    if not current_company and company_code:
        s_res = supabase.table("settings").select("company_name").eq("company_code", company_code).execute()
        if s_res.data:
            current_company = s_res.data[0].get('company_name', "متجر")

    region_name = ""
    if country == 'algeria':
        wilaya = request.form.get('wilaya')
        region_name = wilaya
        try:
            w_res = supabase.table("shipping_rates").select("wilaya_name").eq("id", wilaya).single().execute()
            if w_res.data and w_res.data.get('wilaya_name'):
                region_name = w_res.data.get('wilaya_name')
        except:
            pass
    elif country == 'jordan':
        jordan_region_id = request.form.get('jordan_region')
        region_name = "الأردن"
        try:
            j_res = supabase.table("jordan_rates").select("governorate_name").eq("id", jordan_region_id).single().execute()
            if j_res.data and j_res.data.get('governorate_name'):
                region_name = f"الأردن - {j_res.data.get('governorate_name')}"
        except:
            pass

    main_product_id = cart_data[0].get('id') if cart_data else (int(product_id) if product_id else None)

    is_souhila_order = (request.path == '/submit-souhila-order') or ('souhila' in request.referrer if request.referrer else False)
    
    order_data = {
        "customer_name": full_name,
        "customer_phone": phone,
        "product_name": ", ".join([f"{item.get('name', item.get('title', 'منتج'))} (x{item.get('quantity', 1)})" for item in cart_data]), 
        "quantity": quantity_ordered,
        "total_price": total_price,
        "status": "قيد الانتظار",
        "state": region_name,
        "baladiya": baladiya,
        "delivery_type": delivery_type,
        "delivery_price": delivery_price,
        "product_id": main_product_id
    }
    
    target_table = "orders"
    if is_souhila_order:
        target_table = "orders_souhila"
    else:
        order_data["company_code"] = company_code

    inserted_order_id = None
    try:
        res_insert = supabase.table(target_table).insert(order_data).execute()
        if res_insert.data and len(res_insert.data) > 0:
            inserted_order_id = res_insert.data[0].get('id')
    except Exception as e:
        print(f"Error inserting order: {e}")

    if is_souhila_order:
        try:
            t_res = supabase.table('site_settings').select('*').in_('key', ['telegram_token', 'telegram_chat_id']).execute()
            s_map = {item['key']: item['value'] for item in t_res.data} if t_res.data else {}
            t_token = s_map.get('telegram_token')
            t_chat_id = s_map.get('telegram_chat_id')
            if t_token and t_chat_id:
                product_names_str = ", ".join([f"{item.get('name', item.get('title', 'منتج'))} (x{item.get('quantity', 1)})" for item in cart_data])
                msg_text = (
                    f"🛒 طلبية جديدة (موقع سهيلة)!\n"
                    f"👤 الاسم: {full_name}\n"
                    f"📞 الهاتف: {phone}\n"
                    f"📦 الدورات/المنتجات: {product_names_str}\n"
                    f"📍 المنطقة/الولاية: {region_name}\n"
                    f"🏘️ البلدية: {baladiya}\n"
                    f"💰 المجموع الكلي: {total_price} دج"
                )
                send_telegram_alert_by_token(t_token, t_chat_id, msg_text)
        except Exception as err:
            print("Telegram souhila alert error:", err)

    return """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>تم الطلب بنجاح</title>
        <style>
            body { font-family: Tahoma, sans-serif; background-color: #f4f7f6; text-align: center; padding-top: 50px; margin: 0; }
            .card { background: white; max-width: 400px; margin: auto; padding: 30px; border-radius: 10px; box-shadow: 0px 4px 10px rgba(0,0,0,0.1); }
            p { color: #555; font-size: 16px; }
            .btn { display: inline-block; margin-top: 20px; background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="card">
             <p>شكراً لثقتكم بنا، سيتم الاتصال بكم قريباً لتأكيد الطلب.</p>
            <a href="/souhila" class="btn">🔙 العودة إلى الموقع</a>
        </div>
    </body>
    </html>
    """

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        company_code = request.form.get('company_code')
        res = supabase.table("settings").select("company_code").eq("company_code", company_code).execute()
        if res.data:
            session['company_code'] = company_code
            return redirect(url_for('dashboard'))
        else:
            return "كود الشركة غير صحيح، يرجى التأكد منه.", 401
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        company_code = request.form.get('company_code')
        company_name = request.form.get('company_name')
        res = supabase.table("settings").select("company_code").eq("company_code", company_code).execute()
        if res.data:
            return "هذا الكود مستخدم بالفعل، يرجى اختيار كود آخر!", 400
        try:
            supabase.table("settings").insert({"company_code": company_code, "company_name": company_name}).execute()
            return "تم إنشاء الحساب بنجاح!"
        except Exception as e:
            return f"حدث خطأ: {e}", 500
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('company_code', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/stats')
@login_required
def stats():
    company_code = session.get('company_code')
    try:
        res = supabase.table("orders").select("*").eq("company_code", company_code).execute()
        orders = res.data or []
    except Exception as e:
        orders = []

    total_revenue = sum(float(order.get("total_price") or 0) for order in orders)
    total_orders_count = len(orders)
    total_expenses = 0.0 

    days_map = {"السبت": 0, "الأحد": 0, "الاثنين": 0, "الثلاثاء": 0, "الأربعاء": 0, "الخميس": 0, "الجمعة": 0}
    day_names_map = {5: "السبت", 6: "الأحد", 0: "الاثنين", 1: "الثلاثاء", 2: "الأربعاء", 3: "الخميس", 4: "الجمعة"}

    monthly_map = {
        "جانفي": 0, "فيفري": 0, "مارس": 0, "أفريل": 0, "ماي": 0, "جوان": 0,
        "جويلية": 0, "أوت": 0, "سبتمبر": 0, "أكتوبر": 0, "نوفمبر": 0, "ديسمبر": 0
    }
    month_names_map = {
        1: "جانفي", 2: "فيفري", 3: "مارس", 4: "أفريل", 5: "ماي", 6: "جوان",
        7: "جويلية", 8: "أوت", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
    }

    current_year = datetime.now().year
    yearly_map = {}
    for y in range(2026, max(current_year + 1, 2027)):
        yearly_map[str(y)] = 0

    for order in orders:
        created_at = order.get("created_at")
        total_price = float(order.get("total_price") or 0)
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                day_name = day_names_map.get(dt.weekday())
                if day_name in days_map:
                    days_map[day_name] += total_price

                month_name = month_names_map.get(dt.month)
                if month_name in monthly_map:
                    monthly_map[month_name] += total_price

                year_str = str(dt.year)
                if year_str not in yearly_map:
                    yearly_map[year_str] = 0
                yearly_map[year_str] += total_price
            except Exception as ex:
                pass

    cleaned_orders = []
    for order in orders:
        cleaned_order = {
            "id": order.get("id"),
            "customer_name": str(order.get("customer_name") or ""),
            "total_price": float(order.get("total_price") or 0),
            "status": str(order.get("status") or ""),
            "created_at": str(order.get("created_at") or ""),
            "product_name": str(order.get("product_name") or "")
        }
        cleaned_orders.append(cleaned_order)

    return render_template(
        'stats.html', 
        orders=cleaned_orders, 
        total_orders_count=total_orders_count, 
        total_revenue=total_revenue,
        total_expenses=total_expenses,
        daily=days_map,
        monthly=monthly_map,
        yearly=yearly_map
    )

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    company_code = session.get('company_code')
    currencies = [
        ("USD", "دولار أمريكي"), ("EUR", "يورو"), ("GBP", "جنيه إسترليني"), ("JPY", "ين ياباني"),
        ("SAR", "ريال سعودي"), ("AED", "درهم إماراتي"), ("DZD", "دينار جزائري"), ("EGP", "جنيه مصري"),
        ("KWD", "دينار كويتي"), ("QAR", "ريال قطري"), ("BHD", "دينار بحريني"), ("OMR", "ريال عماني"),
        ("JOD", "دينار أردني"), ("LBP", "ليرة لبنانية"), ("LYD", "دينار ليبي"), ("MAD", "درهم مغربي"),
        ("TND", "دينار تونسي"), ("IQD", "دينار عراقي"), ("SYP", "ليرة سورية"), ("YER", "ريال يمني"),
        ("TRY", "ليرة تركية"), ("AUD", "دولار أسترالي"), ("CAD", "دولار كندي"), ("CHF", "فرنك سويسري"),
        ("CNY", "يوان صيني"), ("INR", "روبية هندية"), ("RUB", "روبل روسي"), ("SGD", "دولار سنغافوري"),
        ("SDG", "جنيه سوداني"), ("MRU", "أوقية موريتانية"), ("SOS", "شلن صومالي"), ("KMF", "فرنك جزر القمر"),
        ("DJF", "فرنك جيبوتي"), ("BND", "دولار بروناي"), ("KRW", "وون كوري جنوبي"), ("MXN", "بيزو مكسيكي")
    ]
    
    if request.method == 'POST':
        data = {
            "company_name": request.form.get('shop_name'),
            "telegram_token": request.form.get('bot_token'),
            "telegram_chat_id": request.form.get('chat_id'),
            "instagram_url": request.form.get('instagram_link'),
            "currency": request.form.get('currency') 
        }
        try:
            supabase.table("settings").update(data).eq("company_code", company_code).execute()
        except Exception as e:
            return f"حدث خطأ أثناء الحفظ: {str(e)}", 500
        return redirect(url_for('settings'))
    
    res = supabase.table("settings").select("*").eq("company_code", company_code).execute()
    settings_data = res.data[0] if res.data else {}
    return render_template('settings.html', settings=settings_data, currencies=currencies)

@app.route('/shipping_settings', methods=['GET'])
@login_required
def shipping_settings():
    return render_template('shipping_settings.html')

@app.route('/shop', methods=['GET', 'POST'])
def shop():
    if request.method == 'POST' and 'company_name' in request.form:
        session['current_shop_name'] = request.form.get('company_name')
        return redirect(url_for('shop'))

    shop_name = session.get('current_shop_name')
    products = []
    if shop_name:
        products = get_products_by_shop_name(shop_name)
    
    return render_template('shop.html', products=products, current_company=shop_name)

@app.route('/clear_session')
def clear_session():
    session.pop('current_shop_name', None)
    return redirect(url_for('shop'))

@app.route('/store2', methods=['GET', 'POST'])
def store2():
    if request.method == 'POST' and 'company_name' in request.form:
        session['current_store2_name'] = request.form.get('company_name')
        return redirect(url_for('store2'))

    shop_name = session.get('current_store2_name')
    products = []
    if shop_name:
        products = get_products_by_shop_name(shop_name)
    
    data = render_template('store2.html', products=products, current_company=shop_name)
    return data

@app.route('/clear_store2_session')
def clear_store2_session():
    session.pop('current_store2_name', None)
    return redirect(url_for('store2'))

@app.route('/store2_cart')
def store2_cart():
    return render_template('store2_cart.html')

@app.route('/store2_checkout_page')
def store2_checkout_page():
    rates = get_wilayas_from_db()
    return render_template('store2_order.html', rates=rates)

@app.route('/store2_checkout/<int:product_id>')
def store2_checkout(product_id):
    product = get_product_from_db(product_id)
    if not product:
        return "المنتج غير موجود", 404
    rates = get_wilayas_from_db()
    return render_template('store2_checkout.html', product=product, rates=rates)


if __name__ == '__main__':
    app.run(debug=True)