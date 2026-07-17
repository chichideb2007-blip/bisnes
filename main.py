from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from collections import defaultdict
from datetime import datetime
from functools import wraps
import os
import time
import requests
from google import genai 

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your_secret_key")

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# إعداد Gemini الجديد
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- الدوال المساعدة ---
def refresh_instagram_token():
    try:
        res = supabase.table("settings").select("value").eq("key", "instagram_token").single().execute()
        if not res.data: return None
        old_token = res.data['value']
        url = f"https://graph.facebook.com/v20.0/oauth/access_token?grant_type=fb_exchange_token&client_id={os.environ.get('APP_ID')}&client_secret={os.environ.get('APP_SECRET')}&fb_exchange_token={old_token}"
        res_meta = requests.get(url).json()
        if 'access_token' in res_meta:
            new_token = res_meta['access_token']
            supabase.table("settings").update({"value": new_token}).eq("key", "instagram_token").execute()
            return new_token
    except Exception as e:
        print(f"Error refreshing token: {e}")
    return None

def send_telegram_alert(company_code, message):
    res = supabase.table("settings").select("telegram_token, telegram_chat_id").eq("company_code", company_code).single().execute()
    if res.data:
        token = res.data.get('telegram_token')
        chat_id = res.data.get('telegram_chat_id')
        if token and chat_id:
            requests.get(f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'company_code' not in session: return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- المسارات ---

@app.route('/webhook_instagram', methods=['GET', 'POST'])
def webhook_instagram():
    if request.method == 'GET':
        if request.args.get('hub.verify_token') == 'MY_VERIFY_TOKEN': return request.args.get('hub.challenge')
        return 'Forbidden', 403
    
    data = request.json
    try:
        msg = data['entry'][0]['messaging'][0]['message']['text']
        # رد ذكي باستخدام Gemini
        response = client.models.generate_content(model='gemini-2.0-flash', contents=f"رد على العميل: {msg}")
        # هنا يتم إضافة كود إرسال الرد لإنستقرام عبر API
        return 'OK', 200
    except: return 'Error', 500

@app.route('/orders', methods=['GET', 'POST'])
@login_required
def orders():
    company_code = session.get('company_code')
    if request.method == 'POST':
        customer = request.form.get('customer_name')
        price = request.form.get('price')
        supabase.table("orders").insert({"customer_name": customer, "total_price": float(price), "company_code": company_code}).execute()
        # إرسال تنبيه للمدير
        send_telegram_alert(company_code, f"🚨 طلبية جديدة: {customer} بمبلغ {price} دج")
        return redirect(url_for('orders'))
    
    orders = supabase.table("orders").select("*").eq("company_code", company_code).execute().data
    return render_template('orders_dashboard.html', orders=orders)

@app.route('/stats')
@login_required
def stats():
    company_code = session.get('company_code')
    orders = supabase.table("orders").select("total_price, created_at").eq("company_code", company_code).execute().data or []
    
    daily = defaultdict(float)
    for o in orders:
        dt = datetime.fromisoformat(o['created_at'].replace('Z', '+00:00'))
        daily[dt.strftime('%A')] += float(o.get('total_price') or 0)
        
    return render_template('stats.html', total_sales=sum(float(o.get('total_price') or 0) for o in orders), daily=dict(daily))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    company_code = session.get('company_code')
    if request.method == 'POST':
        supabase.table("settings").update({
            "telegram_token": request.form.get('telegram_token'),
            "telegram_chat_id": request.form.get('chat_id')
        }).eq("company_code", company_code).execute()
    
    res = supabase.table("settings").select("*").eq("company_code", company_code).execute()
    return render_template('settings.html', settings=res.data[0] if res.data else {})

@app.route('/products')
@login_required
def products():
    company_code = session.get('company_code')
    items = supabase.table("inventory").select("*").eq("company_code", company_code).execute().data
    return render_template('products.html', products=items)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['company_code'] = request.form.get('company_code')
        return redirect(url_for('dashboard'))
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)
