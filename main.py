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
    phone = ""
    whatsapp = ""
    email = ""
    website = ""
    commercial_phone = ""
    
    try:
        settings_res = supabase.table('settings').select('*').limit(1).execute()
        if settings_res.data:
            s_data = settings_res.data[0]
            phone = s_data.get('souhila_phone', '')
            whatsapp = s_data.get('souhila_whatsapp', '')
            email = s_data.get('souhila_email', '')
            website = s_data.get('souhila_website', '')
            commercial_phone = s_data.get('souhila_commercial_phone', '')
    except Exception as e:
        pass
    
    courses_res = supabase.table('souhila_courses').select('*').execute()
    courses = courses_res.data if courses_res.data else []
    
    return render_template('souhila.html', 
                           phone_number=phone, 
                           whatsapp_number=whatsapp, 
                           email_address=email, 
                           website_url=website,
                           commercial_phone=commercial_phone,
                           courses=courses)

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    msg = None

    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        try:
            check_s = supabase.table('settings').select('id').limit(1).execute()
            if not check_s.data:
                supabase.table('settings').insert({'company_code': 'default'}).execute()
        except Exception as e:
            pass

        try:
            all_s = supabase.table('settings').select('id').limit(1).execute()
            if all_s.data:
                rec_id = all_s.data[0]['id']
                
                # 1. تحديث معلومات الاتصال الشاملة (مع المعالجة الذكية للسجل التجاري)
                if form_type == 'contact_update':
                    comm_phone = request.form.get('commercial_phone', '').strip()
                    
                    # نحاول معرفة نوع العمود في قاعدة البيانات أو إرسال القيمة بشكل آمن
                    # إذا أدخل المستخدم أرقاماً بحتة نرسلها كـ int، وإذا تركها فارغة نرسل None
                    if comm_phone.isdigit():
                        comm_phone_value = int(comm_phone)
                    elif comm_phone == "":
                        comm_phone_value = None
                    else:
                        # لو أدخل حروفاً أو رموزاً نجعلها نصاً (في حال كان العمود من نوع نص text)
                        comm_phone_value = comm_phone

                    update_data = {
                        'souhila_phone': request.form.get('phone_number'),
                        'souhila_whatsapp': request.form.get('whatsapp_number'),
                        'souhila_email': request.form.get('email_address'),
                        'souhila_website': request.form.get('website_url'),
                        'souhila_commercial_phone': comm_phone_value
                    }
                    
                    supabase.table('settings').update(update_data).eq('id', rec_id).execute()
                    msg = "Informations de contact mises à jour avec succès !"

                # 2. إضافة دورة
                elif form_type == 'add_course':
                    title = request.form.get('course_title')
                    desc = request.form.get('course_desc')
                    image_file = request.files.get('course_image')
                    
                    image_url = ""
                    if image_file and image_file.filename != '':
                        img_binary = image_file.read()
                        encoded_img = base64.b64encode(img_binary).decode('utf-8')
                        image_url = f"data:{image_file.content_type};base64,{encoded_img}"
                        
                    supabase.table('souhila_courses').insert({
                        'title': title,
                        'description': desc,
                        'image': image_url,
                        'company_code': 'default'
                    }).execute()
                    msg = "Formation ajoutée avec succès !"

                # 3. حذف دورة
                elif form_type == 'delete_course':
                    course_id = request.form.get('course_id')
                    supabase.table('souhila_courses').delete().eq('id', course_id).execute()
                    msg = "Formation supprimée avec succès !"
        except Exception as e:
            print(f"Error in admin POST: {e}")
            msg = f"Erreur lors de la mise à jour: {e}"

    settings_data = {}
    try:
        settings_res = supabase.table('settings').select('*').limit(1).execute()
        if settings_res.data:
            settings_data = settings_res.data[0]
    except Exception as e:
        pass

    courses_res = supabase.table('souhila_courses').select('*').execute()
    courses = courses_res.data if courses_res.data else []

    return render_template('admin.html', 
                           settings=settings_data,
                           msg=msg, 
                           courses=courses)

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

    order_data = {
        "customer_name": full_name,
        "customer_phone": phone,
        "product_name": ", ".join([f"{item.get('name', 'منتج')} (x{item.get('quantity', 1)})" for item in cart_data]), 
        "quantity": quantity_ordered,
        "total_price": total_price,
        "company_code": company_code,
        "status": "قيد الانتظار",
        "state": region_name,
        "baladiya": baladiya,
        "delivery_type": delivery_type,
        "delivery_price": delivery_price,
        "product_id": main_product_id
    }
    
    inserted_order_id = None
    try:
        res_insert = supabase.table("orders").insert(order_data).execute()
        if res_insert.data and len(res_insert.data) > 0:
            inserted_order_id = res_insert.data[0].get('id')
    except Exception as e:
        print(f"Error inserting order: {e}")

    for item in cart_data:
        p_id = item.get('id') or item.get('product_id') or item.get('productId')
        p_name = item.get('name')
        item_qty = int(item.get('quantity', 1))
        
        try:
            prod_info = None
            if p_id:
                prod_res = supabase.table("inventory").select("id, name, quantity").eq("id", p_id).execute()
                if prod_res.data and len(prod_res.data) > 0:
                    prod_info = prod_res.data[0]
            elif p_name:
                prod_res = supabase.table("inventory").select("id, name, quantity").eq("name", p_name).eq("company_id_text", company_code).execute()
                if prod_res.data and len(prod_res.data) > 0:
                    prod_info = prod_res.data[0]

            if prod_info:
                real_p_id = prod_info.get('id')
                current_qty = int(prod_info.get('quantity', 0))
                product_name_db = prod_info.get('name', 'منتج')
                
                new_qty = max(0, current_qty - item_qty)
                supabase.table("inventory").update({"quantity": new_qty}).eq("id", real_p_id).execute()
                
                if new_qty <= 0:
                    send_telegram_alert(product_name_db, current_company, company_code)
        except Exception as ex:
            pass

    if company_code:
        res_settings = supabase.table("settings").select("telegram_token, telegram_chat_id").eq("company_code", company_code).execute()
        if res_settings.data:
            s = res_settings.data[0]
            token, chat_id = s.get('telegram_token'), s.get('telegram_chat_id')
            product_names_str = ", ".join([f"{item.get('name', 'منتج')} (x{item.get('quantity', 1)})" for item in cart_data])
            if token and chat_id:
                delivery_text = "توصيل للمنزل" if delivery_type == "home" else "توصيل للمكتب"
                msg = (
                    f"🛒 طلبية جديدة!\n"
                    f"👤 الاسم: {full_name}\n"
                    f"📞 الهاتف: {phone}\n"
                    f"📦 المنتجات: {product_names_str}\n"
                    f"📍 المنطقة/الولاية: {region_name}\n"
                    f"🏘️ البلدية: {baladiya}\n"
                    f"🏠 العنوان: {address}\n"
                    f"🚚 التوصيل: {delivery_text} ({delivery_price} دج)\n"
                    f"💰 المجموع الكلي: {total_price} دج"
                )
                if inserted_order_id:
                    send_order_alert(token, chat_id, msg, inserted_order_id)
                else:
                    send_telegram_alert_by_token(token, chat_id, msg)

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
            <a href="/store2" class="btn">🔙 العودة إلى المتجر</a>
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

@app.route('/get_delivery_prices', methods=['GET'])
@login_required
def get_delivery_prices():
    company_code = session.get('company_code')
    data = supabase.table("delivery_prices").select("*").eq("company_code", company_code).execute()
    return jsonify(data.data)

@app.route('/update_delivery_price', methods=['POST'])
@login_required
def update_delivery_price():
    data = request.json
    row_id = data.get('id')
    new_office = data.get('office_price')
    new_home = data.get('home_price')
    
    try:
        supabase.table("shipping_rates").update({
            "office_price": new_office,
            "home_price": new_home
        }).eq("id", row_id).execute()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_shipping_rates')
def get_shipping_rates():
    company_code = request.args.get('company_code')
    delivery_type = request.args.get('type') 
    
    try:
        res = supabase.table("delivery_prices") \
            .select("home_price, office_price") \
            .eq("company_code", company_code) \
            .single().execute()
        if res.data:
            price = res.data.get('home_price') if delivery_type == 'home' else res.data.get('office_price')
            return jsonify({"price": float(price or 0)})
    except Exception as e:
        pass
    return jsonify({"price": 0})

@app.route('/get_all_shipping_rates', methods=['GET'])
@login_required
def get_all_shipping_rates():
    res = supabase.table("shipping_rates").select("*").order("id").execute()
    return jsonify(res.data)

@app.route('/update_delivery_settings', methods=['POST'])
@login_required
def update_delivery_settings():
    data = request.json
    company_code = session.get('company_code')
    supabase.table("company_settings").update({
        "delivery_office_price": data.get('office_price'),
        "delivery_home_price": data.get('home_price')
    }).eq("company_code", company_code).execute()
    return jsonify({"status": "success"})

@app.route('/admin/jordan-shipping')
@login_required
def admin_jordan_shipping():
    res = supabase.table("jordan_rates").select("*").order("id").execute()
    jordan_rates = res.data if res.data else []
    return render_template('admin_jordan.html', jordan_rates=jordan_rates)

@app.route('/admin/update-jordan-rate/<int:id>', methods=['POST'])
@login_required
def update_jordan_rate(id):
    try:
        if request.is_json:
            data = request.json
            home_price = data.get('home_price')
            office_price = data.get('office_price')
        else:
            home_price = request.form.get('home_price')
            office_price = request.form.get('office_price')

        supabase.table("jordan_rates").update({
            "home_price": float(home_price or 0),
            "office_price": float(office_price or 0)
        }).eq("id", id).execute()

        if request.is_json:
            return jsonify({"status": "success"})
        return redirect(url_for('orders'))
    except Exception as e:
        if request.is_json:
            return jsonify({"status": "error", "message": str(e)}), 500
        return f"حدث خطأ: {e}", 500

@app.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    company_code = session.get('company_code')
    
    if request.method == 'POST':
        file = request.files.get('product_image')
        encoded_string = ""
        if file and file.filename != '':
            encoded_string = f'data:image/jpeg;base64,{base64.b64encode(file.read()).decode("utf-8")}'

        data = {
            'name': request.form.get('name'),
            'quantity': int(request.form.get('quantity', 0)),
            'price': float(request.form.get('price', 0.0)),
            'company_id_text': company_code,
            'product-images': encoded_string
        }
        try:
            supabase.table('inventory').insert(data).execute()
            return redirect(url_for('products'))
        except Exception as e:
            return f"خطأ في قاعدة البيانات: {str(e)}", 500

    res = supabase.table("inventory").select("*").eq("company_id_text", company_code).execute()
    return render_template('products.html', products=res.data or [])

@app.route('/inventory_management', methods=['GET', 'POST'])
@login_required
def inventory_management():
    company_code = session.get('company_code')
    
    if request.method == 'POST':
        product_id = request.form.get('product_id')
        new_quantity = request.form.get('quantity')
        file = request.files.get('product_image')
        
        update_data = {"quantity": int(new_quantity)}
        
        if file and file.filename != '':
            filename = f"{company_code}/{int(time.time())}_{file.filename}"
            supabase.storage.from_("products").upload(
                path=filename,
                file=file.read(),
                file_options={"content-type": file.content_type}
            )
            public_url = supabase.storage.from_("products").get_public_url(filename)
            update_data["product-images"] = public_url
        
        try:
            supabase.table('inventory').update(update_data).eq("id", product_id).eq("company_id_text", company_code).execute()
        except Exception as e:
            pass
            
    try:
        res = supabase.table("inventory").select("*").eq("company_id_text", company_code).execute()
        inventory_data = res.data or []
    except Exception as e:
        inventory_data = []
        
    return render_template('inventory_management.html', inventory=inventory_data)

@app.route('/edit_product/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    company_code = session.get('company_code')
    res = supabase.table("inventory").select("*").eq("id", id).eq("company_id_text", company_code).execute()
    product = res.data[0] if res.data else None
    
    if not product:
        return "المنتج غير موجود", 404

    if request.method == 'POST':
        new_name = request.form.get('name')
        new_quantity = request.form.get('quantity')
        new_price = request.form.get('price')
        
        supabase.table("inventory").update({
            "name": new_name,
            "quantity": int(new_quantity),
            "price": float(new_price)
        }).eq("id", id).execute()
        
        return redirect(url_for('products'))
        
    return render_template('edit_product.html', product=product)

@app.route('/update_quantity/<int:product_id>', methods=['POST'])
@login_required
def update_quantity(product_id):
    company_code = session.get('company_code')
    action_type = request.form.get('action_type')
    amount = int(request.form.get('amount', 0))
    
    prod = supabase.table("inventory").select("quantity").eq("id", product_id).eq("company_id_text", company_code).single().execute()
    
    if prod.data:
        current_qty = prod.data.get('quantity', 0)
        if action_type == 'add':
            new_qty = current_qty + amount
        else:
            new_qty = amount
            
        supabase.table("inventory").update({"quantity": new_qty}).eq("id", product_id).execute()
        
    return redirect(url_for('products'))

@app.route('/delete_product/<int:id>', methods=['POST'])
@login_required
def delete_product(id):
    try: 
        supabase.table("inventory").delete().eq("id", id).execute()
    except Exception as e: 
        pass
    return redirect(url_for('products'))

@app.route('/delete_order/<int:id>', methods=['POST'])
@login_required
def delete_order(id):
    supabase.table("orders").delete().eq("id", id).execute()
    return redirect(url_for('orders'))

@app.route('/update_status/<int:order_id>', methods=['POST'])
@login_required
def update_status(order_id):
    new_status = request.form.get('status')
    if new_status:
        supabase.table("orders").update({"status": new_status}).eq("id", order_id).execute()
    return redirect(url_for('orders'))

@app.route('/orders', methods=['GET', 'POST'])
@login_required
def orders():
    company_code = session.get('company_code')
    
    if request.method == 'POST':
        product_name = request.form.get('product_name')
        requested_qty = int(request.form.get('quantity', 1))
        customer_name = request.form.get('customer_name')
        customer_phone = request.form.get('customer_phone')
        state = request.form.get('state')
        delivery_type = request.form.get('delivery_type')
        delivery_price = float(request.form.get('delivery_price', 0.0))
        base_price = float(request.form.get('price', 0.0))
        total_price = base_price + delivery_price

        product_res = supabase.table("inventory").select("id, quantity").eq("name", product_name).eq("company_id_text", company_code).execute()
        
        prod_id = None
        if product_res.data:
            product = product_res.data[0]
            prod_id = product['id']
            current_qty = product['quantity']
            new_qty = max(0, current_qty - requested_qty)
            supabase.table("inventory").update({"quantity": new_qty}).eq("id", prod_id).execute()

        order_data = {
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "product_name": product_name,
            "quantity": requested_qty,
            "total_price": total_price,
            "company_code": company_code,
            "status": "قيد الانتظار",
            "state": state,
            "delivery_type": delivery_type,
            "delivery_price": delivery_price,
            "product_id": prod_id
        }
        
        res_insert = supabase.table("orders").insert(order_data).execute()
        inserted_order_id = res_insert.data[0].get('id') if res_insert.data else None
        
        res_settings = supabase.table("settings").select("telegram_token, telegram_chat_id").eq("company_code", company_code).execute()
        if res_settings.data:
            s = res_settings.data[0]
            token = s.get('telegram_token')
            chat_id = s.get('telegram_chat_id')
            if token and chat_id:
                msg = f"🛒 طلبية جديدة من لوحة التحكم!\nالعميل: {customer_name}\nالمنتج: {product_name}\nالكمية: {requested_qty}\nالولاية: {state}"
                if inserted_order_id:
                    send_order_alert(token, chat_id, msg, inserted_order_id)
                else:
                    send_telegram_alert_by_token(token, chat_id, msg)
        
        return redirect(url_for('orders'))

    orders_res = supabase.table("orders").select("*").eq("company_code", company_code).execute()
    wilayas_res = supabase.table("shipping_rates").select("*").order("id").execute()
    jordan_res = supabase.table("jordan_rates").select("*").order("id").execute()
    
    return render_template('orders_dashboard.html', 
                           orders=orders_res.data or [], 
                           data=wilayas_res.data or [],
                           jordan_rates=jordan_res.data or [])

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

if __name__ =='__main__':
    app.run(debug=True)