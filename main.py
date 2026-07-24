from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from supabase import create_client
from collections import defaultdict
from datetime import datetime
from functools import wraps
import os
import time
import requests
import urllib.parse
import base64
from google import genai  # مكتبة Gemini
from google.genai import types # استيراد الأنواع اللازمة للـ Config

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fallback_dev_key")

# إعداد Supabase و Gemini
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- المعالج التلقائي للعملة (مُحدث) ---
@app.context_processor
def inject_currency():
    company_code = session.get('company_code')
    if company_code:
        try:
            # نجلب العملة مرة واحدة للمتجر
            res = supabase.table('settings').select("currency").eq("company_code", company_code).single().execute()
            if res.data:
                return dict(currency=res.data.get('currency', ''))
        except:
            pass
    return dict(currency='DA') # العملة الافتراضية إذا لم توجد

# --- الدوال المساعدة ---

def send_telegram_alert_by_token(token, chat_id, message):
    if not token or not chat_id:
        print("DEBUG: فشل إرسال التنبيه - التوكن أو Chat ID فارغ")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        params = {"chat_id": chat_id, "text": message}
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            print("DEBUG: تم إرسال التنبيه إلى تيلجرام بنجاح!")
            return True
        else:
            print(f"DEBUG: فشل الإرسال. الكود: {response.status_code}, الرد: {response.text}")
            return False
    except Exception as e:
        print(f"DEBUG: خطأ في الاتصال بتليجرام: {e}")
        return False

# دالة مساعدة لعمل `submit_order`
def get_delivery_price(wilaya, delivery_type):
    return 500  # سعر افتراضي

def refresh_instagram_token():
    res = supabase.table("settings").select("company_code, instagram_token").execute()
    for row in res.data:
        old_token = row.get('instagram_token')
        if old_token:
            url = f"https://graph.facebook.com/v20.0/oauth/access_token?grant_type=fb_exchange_token&client_id={os.environ.get('APP_ID')}&client_secret={os.environ.get('APP_SECRET')}&fb_exchange_token={old_token}"
            try:
                response = requests.get(url).json()
                new_token = response.get('access_token')
                if new_token:
                    supabase.table("settings").update({"instagram_token": new_token}).eq("company_code", row['company_code']).execute()
            except Exception as e:
                print(f"Token Refresh Error: {e}")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'company_code' not in session: return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- المسارات ---

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        company_code = request.form.get('company_code')
        
        print(f"DEBUG: الكود الذي تم إدخاله هو: {company_code}")
        res = supabase.table("settings").select("company_code").eq("company_code", company_code).execute()
        print(f"DEBUG: بيانات قاعدة البيانات المسترجعة: {res.data}")
        
        if res.data:
            session['company_code'] = company_code
            return redirect(url_for('dashboard'))
        else:
            return "كود الشركة غير صحيح، يرجى التأكد منه أو إنشاء حساب جديد.", 401
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
            response = supabase.table("settings").insert({
                "company_code": company_code, 
                "company_name": company_name
            }).execute()
            print("DEBUG: تم إضافة الشركة بنجاح:", response.data) 
            return "تم إنشاء الحساب بنجاح!"
        except Exception as e:
            print(f"DEBUG ERROR: حدث خطأ أثناء الإضافة: {e}")
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

# --- مسارات API لأسعار التوصيل الجديدة ---
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
    print(f"DEBUG: البيانات المستلمة هي: {data}")
    
    row_id = data.get('id')
    new_office = data.get('office_price')
    new_home = data.get('home_price')
    
    supabase.table("delivery_prices").update({
        "office_price": new_office,
        "home_price": new_home
    }).eq("id", row_id).execute()
    
    return jsonify({"status": "success"})

# --- مسار الحصول على سعر التوصيل ---
@app.route('/get_delivery_price')
def get_delivery_price():
    company_code = request.args.get('company_code')
    delivery_type = request.args.get('type')
    
    try:
        # جلب أسعار التوصيل من جدول إعدادات الشركة بناءً على كود الشركة
        response = supabase.table("company_settings").select("delivery_home_price, delivery_office_price").eq("company_code", company_code).single().execute()
        settings = response.data
        
        if not settings:
            return jsonify({"price": 0})
        
        # اختيار السعر بناءً على نوع التوصيل
        if delivery_type == 'home':
            price = settings.get('delivery_home_price', 0)
        else:
            price = settings.get('delivery_office_price', 0)
            
        return jsonify({"price": float(price)})
    except Exception as e:
        print(f"DEBUG: خطأ في جلب سعر التوصيل: {e}")
        return jsonify({"price": 0})

# --- المسارات الجديدة المضافة ---
@app.route('/get_delivery_settings', methods=['GET'])
@login_required
def get_delivery_settings():
    company_code = session.get('company_code')
    data = supabase.table("company_settings").select("*").eq("company_code", company_code).single().execute()
    return jsonify(data.data)

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
            print(f"DEBUG ERROR: {e}")
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
            print(f"DEBUG: خطأ في تحديث المخزون: {e}")
            
    try:
        res = supabase.table("inventory").select("*").eq("company_id_text", company_code).execute()
        inventory_data = res.data or []
    except Exception as e:
        print(f"DEBUG: خطأ في جلب المخزون: {e}")
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

@app.route('/delete_product/<int:id>', methods=['POST'])
@login_required
def delete_product(id):
    try: supabase.table("inventory").delete().eq("id", id).execute()
    except Exception as e: print(f"Delete Error: {e}")
    return redirect(url_for('products'))

@app.route('/delete_order/<int:id>', methods=['POST'])
@login_required
def delete_order(id):
    supabase.table("orders").delete().eq("id", id).execute()
    return redirect(url_for('orders'))

@app.route('/orders', methods=['GET', 'POST'])
@login_required
def orders():
    company_code = session.get('company_code')
    
    wilayas_res = supabase.table("shipping_rates").select("*").order("id").execute()
    
    if request.method == 'POST':
        product_name = request.form.get('product_name')
        requested_qty = int(request.form.get('quantity', 0))
        customer_name = request.form.get('customer_name')
        
        state = request.form.get('state')
        delivery_type = request.form.get('delivery_type')
        delivery_price = float(request.form.get('delivery_price', 0.0))
        
        base_price = float(request.form.get('price', 0.0))
        total_price = base_price + delivery_price
        
        data = {
            "customer_name": customer_name,
            "customer_phone": request.form.get('customer_phone'), 
            "product_name": product_name,
            "quantity": requested_qty, 
            "total_price": total_price,
            "company_code": company_code,
            "status": "قيد الانتظار",
            "state": state,
            "delivery_type": delivery_type,
            "delivery_price": delivery_price
        }
        supabase.table("orders").insert(data).execute()
        
        res_settings = supabase.table("settings").select("telegram_token, telegram_chat_id").eq("company_code", company_code).execute()
        settings_info = res_settings.data[0] if res_settings.data else {}
        token = settings_info.get('telegram_token')
        chat_id = settings_info.get('telegram_chat_id')
        
        if token and chat_id:
            msg = f"🛒 طلبية جديدة!\nالعميل: {customer_name}\nالمنتج: {product_name}\nالكمية: {requested_qty}\nالولاية: {state}\nالتوصيل: {delivery_type} ({delivery_price})"
            send_telegram_alert_by_token(token, chat_id, msg)
            
            products_res = supabase.table("inventory").select("id, quantity").eq("name", product_name).eq("company_id_text", company_code).execute()
            
            if products_res.data:
                product = products_res.data[0]
                current_qty = product['quantity']
                new_qty = max(0, current_qty - requested_qty)
                supabase.table("inventory").update({"quantity": new_qty}).eq("id", product['id']).execute()
                
                if new_qty == 0:
                    send_telegram_alert_by_token(token, chat_id, f"❌ تنبيه هام!\nالمنتج '{product_name}' قد نفذ تماماً من المخزون.")
                elif new_qty <= 5:
                    send_telegram_alert_by_token(token, chat_id, f"⚠️ تنبيه مخزون!\nالمنتج '{product_name}' أوشك على النفاذ، المتبقي حالياً: {new_qty}")
            
        return redirect(url_for('orders'))

    res = supabase.table("orders").select("*").eq("company_code", company_code).execute()
    
    return render_template('orders_dashboard.html', orders=res.data or [], wilayas=wilayas_res.data)

@app.route('/shop')
def shop():
    response = supabase.table("inventory").select("*").execute()
    products = response.data
    return render_template('shop.html', products=products)

@app.route('/product/<int:product_id>')
def product_details(product_id):
    response = supabase.table("inventory").select("*").eq("id", product_id).single().execute()
    product = response.data
    return render_template('product_view.html', product=product)

@app.route('/submit-order', methods=['POST'])
def submit_order():
    data = request.form
    customer_name = data.get('customer_name')
    customer_last_name = data.get('customer_last_name')
    phone = data.get('phone')
    product_id = data.get('product_id')
    wilaya_id = data.get('wilaya') 
    delivery_type = data.get('delivery_type') 
    
    product_res = supabase.table("inventory").select("price, name, company_id_text").eq("id", product_id).single().execute()
    product = product_res.data
    
    shipping_res = supabase.table("delivery_prices").select("home_price, office_price").eq("id", int(wilaya_id)).single().execute()
    shipping_data = shipping_res.data
    
    delivery_price = float(shipping_data['home_price']) if delivery_type == 'home' else float(shipping_data['office_price'])
    base_price = float(product['price'])
    total_price = base_price + delivery_price
    
    order_data = {
        "customer_name": f"{customer_name} {customer_last_name}",
        "customer_phone": phone,
        "product_name": product['name'],
        "total_price": total_price,
        "delivery_price": delivery_price,
        "status": "قيد الانتظار",
        "company_code": product['company_id_text']
    }
    supabase.table("orders").insert(order_data).execute()
    
    supabase.rpc('decrement_stock', {'p_id': int(product_id), 'qty': 1}).execute()
    
    settings_res = supabase.table("settings").select("telegram_token, telegram_chat_id").eq("company_code", product['company_id_text']).execute()
    if settings_res.data:
        token = settings_res.data[0]['telegram_token']
        chat_id = settings_res.data[0]['telegram_chat_id']
        message = f"طلب جديد! 📦\nالمنتج: {product['name']}\nالزبون: {customer_name}\nالهاتف: {phone}\nالمجموع: {total_price} دج"
        send_telegram_alert_by_token(token, chat_id, message)
    
    return "تم استلام طلبك بنجاح! سنتصل بك قريباً."

@app.route('/order/<int:product_id>')
def order_page(product_id):
    response = supabase.table("inventory").select("*").eq("id", product_id).single().execute()
    product = response.data
    if not product:
        return "هذا المنتج غير موجود", 404
    return render_template('order.html', product=product)

@app.route('/stats')
@login_required
def stats():
    company_code = session.get('company_code')
    total_sales = 0
    total_expenses = 0
    total_orders = 0
    daily, monthly, yearly = {}, {}, {}

    try:
        res_orders = supabase.table("orders").select("total_price, created_at").eq("company_code", company_code).execute()
        orders = res_orders.data or []
        total_orders = len(orders)
        
        res_expenses = supabase.table("expenses").select("amount, created_at").eq("company_code", company_code).execute()
        expenses = res_expenses.data or []
        total_expenses = sum(float(e.get('amount') or 0) for e in expenses)

        daily_data, monthly_data, yearly_data = defaultdict(float), defaultdict(float), defaultdict(float)
        days_order = ["السبت", "الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
        months_order = ["جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان", "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
        
        for o in orders:
            price = float(o.get('total_price') or 0)
            total_sales += price
            if o.get('created_at'):
                dt = datetime.fromisoformat(o['created_at'].replace('Z', '+00:00'))
                day_name = days_order[dt.weekday()] if dt.weekday() < 7 else "السبت"
                daily_data[day_name] += price
                monthly_data[months_order[dt.month - 1]] += price
                yearly_data[str(dt.year)] += price
        
        daily, monthly, yearly = dict(daily_data), dict(monthly_data), dict(yearly_data)

    except Exception as e:
        print(f"DEBUG: خطأ في صفحة الإحصائيات: {e}")
        
    return render_template('stats.html', total_sales=total_sales, total_expenses=total_expenses, total_orders=total_orders, daily=daily, monthly=monthly, yearly=yearly)

@app.route('/webhook_instagram', methods=['GET', 'POST'])
def webhook_instagram():
    if request.method == 'GET': 
        return request.args.get('hub.challenge')
    
    data = request.json
    try:
        page_id = data['entry'][0]['id']
        messaging = data['entry'][0]['messaging'][0]
        msg = messaging['message']['text']
        sender_id = messaging['sender']['id']
        
        res = supabase.table("settings").select("telegram_token, telegram_chat_id").eq("instagram_page_id", page_id).execute()
        
        if res.data:
            send_telegram_alert_by_token(res.data[0]['telegram_token'], res.data[0]['telegram_chat_id'], f"🔔 رسالة إنستقرام جديدة من العميل ({sender_id}):\n{msg}")
            
        return "OK", 200

    except Exception as e:
      return "Error", 500

if __name__ == '__main__':
    app.run(debug=True)