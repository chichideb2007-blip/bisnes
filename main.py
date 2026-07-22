from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from collections import defaultdict
from datetime import datetime
from functools import wraps
import os
import time
import requests
import base64
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
            res = supabase.table("settings").select("currency").eq("company_code", company_code).execute()
            currency = res.data[0]['currency'] if res.data else ""
            return dict(currency=currency)
        except:
            return dict(currency="")
    return dict(currency="")

# --- الدوال المساعدة ---

def send_telegram_alert_by_token(token, chat_id, message):
    if not token or not chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        params = {"chat_id": chat_id, "text": message}
        response = requests.get(url, params=params)
        return response.status_code == 200
    except Exception as e:
        print(f"DEBUG: خطأ في الاتصال بتليجرام: {e}")
        return False

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

# --- المسارات الأصلية ---

@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        company_code = request.form.get('company_code')
        res = supabase.table("settings").select("company_code").eq("company_code", company_code).execute()
        if res.data:
            session['company_code'] = company_code
            return redirect(url_for('dashboard'))
        return "كود الشركة غير صحيح!", 401
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        company_code = request.form.get('company_code')
        company_name = request.form.get('company_name')
        if supabase.table("settings").select("company_code").eq("company_code", company_code).execute().data:
            return "هذا الكود مستخدم بالفعل!", 400
        supabase.table("settings").insert({"company_code": company_code, "company_name": company_name}).execute()
        return "تم إنشاء الحساب بنجاح!"
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('company_code', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard(): return render_template('dashboard.html')

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    company_code = session.get('company_code')
    if request.method == 'POST':
        data = {
            "company_name": request.form.get('shop_name'),
            "telegram_token": request.form.get('bot_token'),
            "telegram_chat_id": request.form.get('chat_id'),
            "currency": request.form.get('currency'),
            "delivery_home_price": float(request.form.get('delivery_home_price', 0)),
            "delivery_office_price": float(request.form.get('delivery_office_price', 0))
        }
        supabase.table("settings").update(data).eq("company_code", company_code).execute()
        return redirect(url_for('settings'))
    res = supabase.table("settings").select("*").eq("company_code", company_code).execute()
    return render_template('settings.html', settings=res.data[0] if res.data else {})

@app.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    company_code = session.get('company_code')
    if request.method == 'POST':
        file = request.files.get('product_image')
        encoded_string = f'data:image/jpeg;base64,{base64.b64encode(file.read()).decode("utf-8")}' if file else ""
        data = {'name': request.form.get('name'), 'quantity': int(request.form.get('quantity', 0)), 'price': float(request.form.get('price', 0.0)), 'company_id_text': company_code, 'product-images': encoded_string}
        supabase.table('inventory').insert(data).execute()
        return redirect(url_for('products'))
    return render_template('products.html', products=supabase.table("inventory").select("*").eq("company_id_text", company_code).execute().data or [])

@app.route('/orders', methods=['GET', 'POST'])
@login_required
def orders():
    company_code = session.get('company_code')
    res_settings = supabase.table("settings").select("*").eq("company_code", company_code).execute()
    settings_info = res_settings.data[0] if res_settings.data else {}
    
    if request.method == 'POST':
        product_name = request.form.get('product_name')
        requested_qty = int(request.form.get('quantity', 0))
        data = {
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('customer_phone'), 
            "product_name": product_name,
            "quantity": requested_qty, 
            "total_price": float(request.form.get('price', 0.0)),
            "company_code": company_code,
            "status": "قيد الانتظار"
        }
        supabase.table("orders").insert(data).execute()
        
        token = settings_info.get('telegram_token')
        chat_id = settings_info.get('telegram_chat_id')
        if token and chat_id:
            msg = f"🛒 طلبية جديدة!\nالعميل: {request.form.get('customer_name')}\nالمنتج: {product_name}"
            send_telegram_alert_by_token(token, chat_id, msg)
            # تحديث المخزون
            inv = supabase.table("inventory").select("id, quantity").eq("name", product_name).eq("company_id_text", company_code).execute().data
            if inv:
                new_qty = max(0, inv[0]['quantity'] - requested_qty)
                supabase.table("inventory").update({"quantity": new_qty}).eq("id", inv[0]['id']).execute()
        return redirect(url_for('orders'))

    return render_template('orders_dashboard.html', orders=supabase.table("orders").select("*").eq("company_code", company_code).execute().data or [], currency=settings_info.get('currency', ''))

@app.route('/webhook_instagram', methods=['GET', 'POST'])
def webhook_instagram():
    if request.method == 'GET': return request.args.get('hub.challenge')
    data = request.json
    try:
        page_id = data['entry'][0]['id']
        messaging = data['entry'][0]['messaging'][0]
        msg = messaging['message']['text']
        sender_id = messaging['sender']['id']
        res = supabase.table("settings").select("telegram_token, telegram_chat_id").eq("instagram_page_id", page_id).execute()
        if res.data:
            s = res.data[0]
            send_telegram_alert_by_token(s['telegram_token'], s['telegram_chat_id'], f"🔔 رسالة من ({sender_id}):\n{msg}")
            # التفاعل عبر Gemini
            my_system_instruction = "أنت مساعد مبيعات ذكي..." 
            response = client.models.generate_content(model='gemini-2.0-flash', contents=msg, config=types.GenerateContentConfig(system_instruction=my_system_instruction))
            send_telegram_alert_by_token(s['telegram_token'], s['telegram_chat_id'], f"🤖 الرد: {response.text}")
        return 'OK', 200
    except Exception as e:
        return 'Error', 500

# --- المسارات الجديدة للمتجر العام ---

@app.route('/shop/<company_code>')
def shop_page(company_code):
    products = supabase.table("inventory").select("*").eq("company_id_text", company_code).execute().data or []
    comp_res = supabase.table("settings").select("company_name").eq("company_code", company_code).execute()
    company_name = comp_res.data[0]['company_name'] if comp_res.data else "متجرنا"
    return render_template('public_shop.html', products=products, company_name=company_name, company_code=company_code)

@app.route('/order/<int:product_id>', methods=['GET', 'POST'])
def finalize_order(product_id):
    # 1. جلب بيانات المنتج
    res = supabase.table("inventory").select("*").eq("id", product_id).execute()
    if not res.data: return "المنتج غير موجود", 404
    product = res.data[0]
    company_code = product['company_id_text']
    
    # 2. جلب أسعار التوصيل الخاصة بالشركة من الإعدادات
    settings_res = supabase.table("settings").select("telegram_token, telegram_chat_id, delivery_home_price, delivery_office_price").eq("company_code", company_code).execute()
    settings = settings_res.data[0] if settings_res.data else {"delivery_home_price": 0, "delivery_office_price": 0}
    
    if request.method == 'POST':
        # التحقق من الكمية
        if product['quantity'] <= 0: return "عذراً، المنتج قد نفذ."

        # 3. حساب المجموع الكلي (سعر المنتج + سعر التوصيل المختار من الفورم)
        shipping = float(request.form.get('shipping_cost', 0))
        total_price = float(product['price']) + shipping
        
        # 4. حفظ الطلب في قاعدة البيانات
        order_data = {
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('customer_phone'),
            "shipping_address": request.form.get('state'),
            "product_name": product['name'],
            "total_price": total_price, # السعر الإجمالي
            "company_code": company_code,
            "status": "قيد الانتظار"
        }
        supabase.table("orders").insert(order_data).execute()
        
        # 5. تنقيص المخزون
        supabase.table("inventory").update({"quantity": product['quantity'] - 1}).eq("id", product_id).execute()
        
        # 6. التنبيه بالتليجرام
        token = settings.get('telegram_token')
        chat_id = settings.get('telegram_chat_id')
        if token and chat_id:
            msg = f"📦 طلبية جديدة عبر الموقع!\nالمنتج: {product['name']}\nالزبون: {request.form.get('customer_name')}\nالمجموع: {total_price}"
            send_telegram_alert_by_token(token, chat_id, msg)
            
        return "تم الطلب بنجاح!"
    
    return render_template('checkout.html', product=product, settings=settings)

if __name__ == '__main__':
    refresh_instagram_token()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
