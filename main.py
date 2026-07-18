from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from collections import defaultdict
from datetime import datetime
from functools import wraps
import os
import time
import requests
import urllib.parse
import base64  # تمت الإضافة
from google import genai  # مكتبة Gemini

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fallback_dev_key")

# إعداد Supabase و Gemini
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- الدوال المساعدة ---

def send_telegram_alert_by_token(token, chat_id, message):
    if token and chat_id:
        try:
            requests.get(f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}")
        except Exception as e:
            print(f"Error: {e}")

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
        res = supabase.table("settings").select("company_code").eq("company_code", company_code).execute()
        if res.data:
            session['company_code'] = company_code
            return redirect(url_for('dashboard'))
        return "كود الشركة غير صحيح!", 401
    return render_template('login.html')

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
            "company_name": request.form.get('company_name'),
            "telegram_token": request.form.get('telegram_token'),
            "telegram_chat_id": request.form.get('chat_id'),
            "instagram_url": request.form.get('instagram_url')
        }
        supabase.table("settings").update(data).eq("company_code", company_code).execute()
        return redirect(url_for('settings'))
    res = supabase.table("settings").select("*").eq("company_code", company_code).execute()
    return render_template('settings.html', settings=res.data[0] if res.data else {})

# مسار المخزون المحدث
@app.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    company_code = session.get('company_code')
    if request.method == 'POST':
        # استقبال الملف من الـ Form
        file = request.files.get('product_image')
        image_data = ""
        if file:
            encoded_string = base64.b64encode(file.read()).decode('utf-8')
            image_data = f"data:image/jpeg;base64,{encoded_string}"
        
        data = {
            "name": request.form.get('name'),
            "quantity": int(request.form.get('quantity', 0)),
            "price": float(request.form.get('price', 0.0)),
            "company_code": company_code,
            "company_id_text": company_code,
            "product-images": image_data
        }
        supabase.table("inventory").insert(data).execute()
        return redirect(url_for('products'))
    
    res = supabase.table("inventory").select("*").eq("company_code", company_code).execute()
    return render_template('products.html', products=res.data or [])

@app.route('/delete_product/<int:id>', methods=['POST'])
@login_required
def delete_product(id):
    supabase.table("inventory").delete().eq("id", id).execute()
    return redirect(url_for('products'))

@app.route('/orders', methods=['GET', 'POST'])
@login_required
def orders():
    company_code = session.get('company_code')
    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "total_price": float(request.form.get('price', 0.0)),
            "company_code": company_code
        }
        supabase.table("orders").insert(data).execute()
        res = supabase.table("settings").select("telegram_token, telegram_chat_id").eq("company_code", company_code).execute()
        if res.data:
            msg = f"🚨 طلبية جديدة!\nالعميل: {data['customer_name']}\nالقيمة: {data['total_price']} دج"
            send_telegram_alert_by_token(res.data[0]['telegram_token'], res.data[0]['telegram_chat_id'], msg)
        return redirect(url_for('orders'))
    res = supabase.table("orders").select("*").eq("company_code", company_code).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

@app.route('/stats')
@login_required
def stats():
    company_code = session.get('company_code')
    res_orders = supabase.table("orders").select("total_price, created_at").eq("company_code", company_code).execute()
    orders = res_orders.data or []
    total_sales = sum(float(o.get('total_price') or 0) for o in orders)
    return render_template('stats.html', total_sales=total_sales, total_orders=len(orders))

@app.route('/webhook_instagram', methods=['GET', 'POST'])
def webhook_instagram():
    if request.method == 'GET': return request.args.get('hub.challenge')
    data = request.json
    try:
        page_id = data['entry'][0]['id']
        msg = data['entry'][0]['messaging'][0]['message']['text']
        sender_id = data['entry'][0]['messaging'][0]['sender']['id']
        res = supabase.table("settings").select("telegram_token, telegram_chat_id").eq("instagram_page_id", page_id).execute()
        if res.data:
            response = client.models.generate_content(model='gemini-2.0-flash', contents=msg)
            send_telegram_alert_by_token(res.data[0]['telegram_token'], res.data[0]['telegram_chat_id'], f"رد Gemini: {response.text}")
        return 'OK', 200
    except: return 'Error', 500

if __name__ == '__main__':
    refresh_instagram_token()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
