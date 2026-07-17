from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from collections import defaultdict
from datetime import datetime
from functools import wraps
import os
import time
import requests
import urllib.parse 

app = Flask(__name__)
# تأكدي من ضبط المفتاح السري في إعدادات الاستضافة
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your_secret_key_here")

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- دالة تجديد التوكن ---
def refresh_and_get_token():
    try:
        response = supabase.table("settings").select("value").eq("key", "instagram_token").single().execute()
        if not response.data: return None
        old_token = response.data['value']
        
        url = f"https://graph.facebook.com/v20.0/oauth/access_token?grant_type=fb_exchange_token&client_id={os.environ.get('APP_ID')}&client_secret={os.environ.get('APP_SECRET')}&fb_exchange_token={old_token}"
        res = requests.get(url).json()
        
        if 'access_token' in res:
            new_token = res['access_token']
            supabase.table("settings").update({"value": new_token}).eq("key", "instagram_token").execute()
            print("تم تجديد التوكن بنجاح!")
            return new_token
    except Exception as e:
        print(f"خطأ في التجديد: {e}")
    return None

# استدعاء الدالة عند بداية تشغيل التطبيق
current_token = refresh_and_get_token()

# --- حماية المسارات ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'company_code' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- المسارات (تم التحديث) ---

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        company_code = request.form.get('company_code') 
        if company_code:
            session['company_code'] = company_code
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# --- باقي المسارات ---

@app.route('/settings', methods=['GET'])
@login_required
def settings():
    company_code = session.get('company_code')
    res = supabase.table("settings").select("*").eq("company_code", company_code).execute()
    settings_data = res.data[0] if res.data else {}
    return render_template('settings.html', settings=settings_data)

@app.route('/update_company', methods=['POST'])
@login_required
def update_company():
    company_code = session.get('company_code')
    data = {
        "company_name": request.form.get('company_name'),
        "telegram_token": request.form.get('telegram_token'),
        "telegram_chat_id": request.form.get('chat_id')
    }
    supabase.table("settings").update(data).eq("company_code", company_code).execute()
    return redirect(url_for('settings'))

@app.route('/instagram_login')
@login_required
def instagram_login():
    app_id = os.environ.get("APP_ID")
    redirect_uri = "https://your-domain.com/callback" 
    scope = "instagram_basic,instagram_manage_messages,pages_show_list,pages_messaging"
    auth_url = f"https://www.facebook.com/v20.0/dialog/oauth?client_id={app_id}&redirect_uri={redirect_uri}&scope={scope}&response_type=code"
    return redirect(auth_url)

@app.route('/webhook_instagram', methods=['GET', 'POST'])
def webhook_instagram():
    if request.method == 'GET':
        if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.verify_token') == 'MY_VERIFY_TOKEN': 
            return request.args.get('hub.challenge')
        return 'Forbidden', 403
    
    data = request.json
    try:
        page_id = data['entry'][0]['id'] 
        res = supabase.table("settings").select("*").eq("instagram_page_id", page_id).execute()
        if res.data:
            company = res.data[0]
            send_telegram_alert_by_token(company.get('telegram_token'), company.get('telegram_chat_id'), "🔔 رسالة جديدة!")
    except Exception as e:
        print(f"Webhook Error: {e}")
    return 'OK', 200

# --- الدوال المساعدة ---

def send_telegram_alert(company_code, message):
    res = supabase.table("settings").select("telegram_token, telegram_chat_id").eq("company_code", company_code).execute()
    if res.data:
        send_telegram_alert_by_token(res.data[0].get('telegram_token'), res.data[0].get('telegram_chat_id'), message)

def send_telegram_alert_by_token(token, chat_id, message):
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
        requests.get(url)

if __name__ == '__main__':
    app.run(debug=True)
