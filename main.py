from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from collections import defaultdict
from datetime import datetime
from functools import wraps
import os
import time
import requests
import urllib.parse
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
    except:
        return False

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
            except: pass

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
        res = supabase.table("settings").select("company_code").eq("company_code", company_code).execute()
        if res.data:
            session['company_code'] = company_code
            return redirect(url_for('dashboard'))
        else:
            return "كود الشركة غير صحيح", 401
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        company_code = request.form.get('company_code')
        company_name = request.form.get('company_name')
        res = supabase.table("settings").select("company_code").eq("company_code", company_code).execute()
        if res.data: return "هذا الكود مستخدم بالفعل", 400
        supabase.table("settings").insert({"company_code": company_code, "company_name": company_name}).execute()
        return "تم إنشاء الحساب بنجاح!"
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
    if request.method == 'POST':
        data = {
            "company_name": request.form.get('shop_name'),
            "telegram_token": request.form.get('bot_token'),
            "telegram_chat_id": request.form.get('chat_id'),
            "instagram_url": request.form.get('instagram_link'),
            "currency": request.form.get('currency') 
        }
        supabase.table("settings").update(data).eq("company_code", company_code).execute()
        return redirect(url_for('settings'))
    res = supabase.table("settings").select("*").eq("company_code", company_code).execute()
    return render_template('settings.html', settings=res.data[0] if res.data else {})

# --- إدارة المخزون ---

@app.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    company_code = session.get('company_code')
    if request.method == 'POST':
        file = request.files.get('product_image')
        encoded_string = f'data:image/jpeg;base64,{base64.b64encode(file.read()).decode("utf-8")}' if file else ""
        data = {
            'name': request.form.get('name'),
            'quantity': int(request.form.get('quantity', 0)),
            'price': float(request.form.get('price', 0.0)),
            'company_id_text': company_code,
            'product-images': encoded_string
        }
        supabase.table('inventory').insert(data).execute()
        return redirect(url_for('products'))
    res = supabase.table("inventory").select("*").eq("company_id_text", company_code).execute()
    return render_template('products.html', products=res.data or [])

@app.route('/inventory_management', methods=['GET', 'POST'])
@login_required
def inventory_management():
    company_code = session.get('company_code')
    if request.method == 'POST':
        product_id = request.form.get('product_id')
        new_quantity = int(request.form.get('quantity'))
        supabase.table('inventory').update({"quantity": new_quantity}).eq("id", product_id).eq("company_id_text", company_code).execute()
    res = supabase.table("inventory").select("*").eq("company_id_text", company_code).execute()
    return render_template('inventory_management.html', inventory=res.data or [])

@app.route('/orders', methods=['GET', 'POST'])
@login_required
def orders():
    company_code = session.get('company_code')
    res_settings = supabase.table("settings").select("*").eq("company_code", company_code).execute()
    settings_info = res_settings.data[0] if res_settings.data else {}
    
    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('customer_phone'), 
            "product_name": request.form.get('product_name'),
            "quantity": int(request.form.get('quantity', 0)), 
            "total_price": float(request.form.get('price', 0.0)),
            "company_code": company_code,
            "status": "قيد الانتظار"
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))

    res = supabase.table("orders").select("*").eq("company_code", company_code).execute()
    return render_template('orders_dashboard.html', orders=res.data or [], currency=settings_info.get('currency', ''))

# --- مسارات الزبائن (تم التعديل لتستخدم جدول inventory) ---

@app.route('/shop')
def shop():
    try:
        response = supabase.table("inventory").select("*").execute()
        return render_template('shop.html', products=response.data or [])
    except Exception as e:
        return f"خطأ: {str(e)}", 500

@app.route('/product/<int:product_id>')
def product_details(product_id):
    response = supabase.table("inventory").select("*").eq("id", product_id).single().execute()
    return render_template('product_view.html', product=response.data)

@app.route('/order/<int:product_id>')
def order_page(product_id):
    response = supabase.table("inventory").select("*").eq("id", product_id).single().execute()
    if not response.data: return "المنتج غير موجود", 404
    return render_template('order.html', product=response.data)

@app.route('/submit-order', methods=['POST'])
def submit_order():
    data = request.form
    product_id = data.get('product_id')
    
    # جلب المنتج من المخزون
    product_res = supabase.table("inventory").select("*").eq("id", product_id).single().execute()
    product = product_res.data
    if not product: return "المنتج غير موجود", 404
    
    # حساب السعر وإضافة الطلب
    total_price = float(product['price']) + get_delivery_price(data.get('wilaya'), data.get('delivery_type'))
    
    order_data = {
        "customer_name": data.get('customer_name'),
        "customer_phone": data.get('phone'),
        "product_name": product['name'],
        "total_price": total_price,
        "status": "pending",
        "company_code": product['company_id_text']
    }
    supabase.table("orders").insert(order_data).execute()
    
    # نقص الكمية
    supabase.rpc('decrement_stock', {'p_id': int(product_id), 'qty': 1}).execute()
    
    # تنبيه المدير
    settings_res = supabase.table("settings").select("telegram_token, telegram_chat_id").eq("company_code", product['company_id_text']).execute()
    if settings_res.data:
        t = settings_res.data[0]
        send_telegram_alert_by_token(t.get('telegram_token'), t.get('telegram_chat_id'), f"📦 طلب جديد!\nالمنتج: {product['name']}\nالزبون: {data.get('customer_name')}")
            
    return "تم استلام طلبك بنجاح!"

# --- مسارات إضافية ---
@app.route('/stats')
@login_required
def stats():
    return render_template('stats.html')

@app.route('/webhook_instagram', methods=['GET', 'POST'])
def webhook_instagram():
    return 'OK', 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
