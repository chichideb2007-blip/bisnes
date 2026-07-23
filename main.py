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
        try:
            supabase.table("settings").insert({"company_code": company_code, "company_name": company_name}).execute()
            return "تم إنشاء الحساب بنجاح!"
        except Exception as e:
            return f"خطأ: {e}", 500
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

@app.route('/orders', methods=['GET', 'POST'])
@login_required
def orders():
    company_code = session.get('company_code')
    res_settings = supabase.table("settings").select("currency, telegram_token, telegram_chat_id").eq("company_code", company_code).execute()
    settings_info = res_settings.data[0] if res_settings.data else {}
    currency = settings_info.get('currency', '')

    if request.method == 'POST':
        # استخراج البيانات
        customer_name = request.form.get('customer_name')
        customer_phone = request.form.get('customer_phone')
        product_name = request.form.get('product_name')
        price = float(request.form.get('price', 0))
        quantity = int(request.form.get('quantity', 0))
        
        # الحقول الجديدة
        state = request.form.get('state')
        delivery_type = request.form.get('delivery_type')
        delivery_price = float(request.form.get('delivery_price', 0))
        
        # حساب الإجمالي
        total_price = price + delivery_price
        
        # إضافة البيانات
        order_data = {
            'customer_name': customer_name,
            'customer_phone': customer_phone,
            'product_name': product_name,
            'quantity': quantity,
            'price': price,
            'state': state,
            'delivery_type': delivery_type,
            'delivery_price': delivery_price,
            'total_price': total_price,
            'company_code': company_code,
            'status': 'قيد الانتظار'
        }
        supabase.table('orders').insert(order_data).execute()
        
        # تنبيه تليجرام
        token = settings_info.get('telegram_token')
        chat_id = settings_info.get('telegram_chat_id')
        if token and chat_id:
            msg = f"🛒 طلبية جديدة!\nالعميل: {customer_name}\nالمنتج: {product_name}\nالولاية: {state}"
            send_telegram_alert_by_token(token, chat_id, msg)
        
        return redirect(url_for('orders'))

    res = supabase.table("orders").select("*").eq("company_code", company_code).execute()
    return render_template('orders_dashboard.html', orders=res.data or [], currency=currency)

# --- باقي المسارات (Products, Inventory, Shop, etc.) ---
# (تم اختصارها للحفاظ على التركيز، أضف بقية المسارات من كودك الأصلي هنا)

@app.route('/shop')
def shop():
    response = supabase.table("inventory").select("*").execute()
    return render_template('shop.html', products=response.data)

@app.route('/stats')
@login_required
def stats():
    company_code = session.get('company_code')
    res_orders = supabase.table("orders").select("total_price, created_at").eq("company_code", company_code).execute()
    orders = res_orders.data or []
    total_sales = sum(float(o.get('total_price') or 0) for o in orders)
    return render_template('stats.html', total_sales=total_sales, total_orders=len(orders))

if __name__ == '__main__':
    app.run(debug=True)
