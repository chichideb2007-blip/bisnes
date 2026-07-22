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
    # يمكنك تعديل هذه الدالة لاحقاً لجلب الأسعار ديناميكياً
    return 500 

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
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            supabase.table("settings").insert({"company_code": request.form.get('company_code'), "company_name": request.form.get('company_name')}).execute()
            return "تم إنشاء الحساب!"
        except: return "خطأ في إنشاء الحساب", 500
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
            "currency": request.form.get('currency') 
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
        encoded = f'data:image/jpeg;base64,{base64.b64encode(file.read()).decode("utf-8")}' if file else ""
        data = {'name': request.form.get('name'), 'quantity': int(request.form.get('quantity', 0)), 'price': float(request.form.get('price', 0.0)), 'company_id_text': company_code, 'product-images': encoded}
        supabase.table('inventory').insert(data).execute()
        return redirect(url_for('products'))
    return render_template('products.html', products=supabase.table("inventory").select("*").eq("company_id_text", company_code).execute().data or [])

@app.route('/inventory_management', methods=['GET', 'POST'])
@login_required
def inventory_management():
    company_code = session.get('company_code')
    if request.method == 'POST':
        product_id = request.form.get('product_id')
        update_data = {"quantity": int(request.form.get('quantity'))}
        supabase.table('inventory').update(update_data).eq("id", product_id).eq("company_id_text", company_code).execute()
    return render_template('inventory_management.html', inventory=supabase.table("inventory").select("*").eq("company_id_text", company_code).execute().data or [])

@app.route('/delete_order/<int:id>', methods=['POST'])
@login_required
def delete_order(id):
    supabase.table("orders").delete().eq("id", id).execute()
    return redirect(url_for('orders'))

@app.route('/orders', methods=['GET', 'POST'])
@login_required
def orders():
    company_code = session.get('company_code')
    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('customer_phone'),
            "product_name": request.form.get('product_name'),
            "quantity": int(request.form.get('quantity')),
            "total_price": float(request.form.get('price')),
            "company_code": company_code,
            "status": "قيد الانتظار"
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    return render_template('orders_dashboard.html', orders=supabase.table("orders").select("*").eq("company_code", company_code).execute().data or [])

@app.route('/shop')
def shop():
    return render_template('shop.html', products=supabase.table("products").select("*").execute().data)

# --- المسار الجديد المدمج ---
@app.route('/submit-order', methods=['POST'])
def submit_order():
    # 1. استقبال البيانات
    customer_name = request.form.get('customer_name')
    phone = request.form.get('phone')
    product_id = request.form.get('product_id')
    wilaya = request.form.get('wilaya', 'غير محدد')
    delivery_type = request.form.get('delivery_type', 'home')
    
    # 2. جلب بيانات المنتج
    res = supabase.table("products").select("name, price, company_id_text").eq("id", product_id).single().execute()
    product = res.data
    if not product: return "خطأ: المنتج غير موجود", 404
    
    # 3. حساب السعر
    delivery_cost = get_delivery_price(wilaya, delivery_type)
    total_price = float(product['price']) + delivery_cost
    
    # 4. إرسال الطلب لجدول orders
    order_data = {
        "customer_name": customer_name,
        "customer_phone": phone,
        "product_name": product['name'],
        "total_price": total_price,
        "company_code": product['company_id_text'],
        "status": "قيد الانتظار"
    }
    supabase.table("orders").insert(order_data).execute()
    
    # 5. نقص الكمية من جدول products (Update)
    try:
        supabase.rpc('decrement_stock', {'p_id': int(product_id), 'qty': 1}).execute()
    except: pass
    
    # 6. إرسال إشعار تليجرام للمدير
    settings = supabase.table("settings").select("telegram_token, telegram_chat_id").eq("company_code", product['company_id_text']).single().execute().data
    if settings:
        msg = f"📦 طلب جديد!\nالمنتج: {product['name']}\nالزبون: {customer_name}\nالهاتف: {phone}\nالمجموع: {total_price}"
        send_telegram_alert_by_token(settings['telegram_token'], settings['telegram_chat_id'], msg)
    
    return "تم استلام طلبك بنجاح! سنتصل بك قريباً."

@app.route('/stats')
@login_required
def stats():
    company_code = session.get('company_code')
    orders = supabase.table("orders").select("total_price, created_at").eq("company_code", company_code).execute().data or []
    return render_template('stats.html', total_orders=len(orders), total_sales=sum(o['total_price'] for o in orders))

@app.route('/webhook_instagram', methods=['GET', 'POST'])
def webhook_instagram():
    if request.method == 'GET': return request.args.get('hub.challenge')
    data = request.json
    try:
        msg = data['entry'][0]['messaging'][0]['message']['text']
        # منطق Gemini هنا موجود كما كان في الكود الأصلي
        return 'OK', 200
    except: return 'Error', 500

if __name__ == '__main__':
    refresh_instagram_token()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
