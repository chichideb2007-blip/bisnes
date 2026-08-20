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

# --- المعالج التلقائي للعملة (مُحدث) ---
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

# --- دالة تنبيه نفاذ المخزون عبر تيليجرام (المحدثة) ---
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
                    print(f"DEBUG: تم إرسال تنبيه نفاذ المخزون للمنتج {product_name}")
                    return
        print("DEBUG: لم يتم العثور على توكن تيليجرام خاص بهذا المحل في الإعدادات.")
    except Exception as e:
        print("Telegram error:", e)

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
        print(f"Error sending order alert with buttons: {e}")
        return False

def get_products_by_shop_name(shop_name):
    try:
        shop_name_decoded = urllib.parse.unquote(shop_name).strip()
        print(f"DEBUG: ابحث عن متجر باسم: {shop_name_decoded}")
        
        settings = supabase.table("settings").select("company_code").ilike("company_name", shop_name_decoded).execute()
        
        if not settings.data:
            print("DEBUG: لم أجد متجراً بهذا الاسم")
            return []
        
        company_code = settings.data[0]['company_code']
        print(f"DEBUG: وجدت الكود: {company_code}")
        
        products = supabase.table("inventory").select("*").eq("company_id_text", company_code).execute()
        
        print(f"DEBUG: المنتجات التي وجدتها لـ {company_code} هي: {len(products.data)}")
        return products.data
    except Exception as e:
        print(f"DEBUG ERROR: {e}")
        return []

def get_delivery_price(wilaya, delivery_type):
    return 500

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
                shop_name = settings_res.data[0].get('company_name')
                session['current_shop_name'] = shop_name
                
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

    # --- خصم المخزون وإرسال تنبيه تيليجرام لكل منتج في السلة ---
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
                print(f"DEBUG: تم خصم {item_qty} من المنتج {product_name_db}. المخزون الجديد: {new_qty}")
                
                if new_qty <= 0:
                    send_telegram_alert(product_name_db, current_company, company_code)
            else:
                print(f"DEBUG: لم يتم العثور على المنتج في قاعدة البيانات لخصم مخزونه: {item}")
                
        except Exception as ex:
            print(f"DEBUG: خطأ في خصم مخزون المنتج: {ex}")

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
            h2 { color: #28a745; }
            p { color: #555; font-size: 16px; }
            .btn { display: inline-block; margin-top: 20px; background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; }
            .btn:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>🎉 تم تأكيد طلبك بنجاح!</h2>
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
                           wilayas=wilayas_res.data or [],
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

@app.route('/store2', methods=['GET', 'POST'])
def store2():
    if request.method == 'POST' and 'company_name' in request.form:
        session['current_store2_name'] = request.form.get('company_name')
        return redirect(url_for('store2'))

    shop_name = session.get('current_store2_name')
    products = []
    if shop_name:
        products = get_products_by_shop_name(shop_name)
    
    return render_template('store2.html', products=products, current_company=shop_name)

if __name__ =='__main__':
    app.run(debug=True)