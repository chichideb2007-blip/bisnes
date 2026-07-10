from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
import requests
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- دالة إرسال الإشعار عبر تيلجرام ---
def send_telegram_notification(comp_id, order_details):
    try:
        settings = supabase.table("company_settings").select("*").eq("company_id_text", comp_id).single().execute()
        if not settings.data: return

        telegram_token = settings.data.get('whatsapp_token')
        chat_id = settings.data.get('manager_phone')
        store_name = settings.data.get('store_name', 'متجرك')
        
        if not telegram_token or not chat_id: return

        url_api = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        body_text = (f"🔔 تنبيه طلبية جديدة من: {store_name}\n\n"
                     f"👤 العميل: {order_details['customer_name']}\n"
                     f"📞 الهاتف: {order_details['customer_phone']}\n"
                     f"📦 المنتج: {order_details['product_name']}\n"
                     f"💰 السعر: {order_details['total_price']} دج")
        
        payload = {"chat_id": chat_id, "text": body_text}
        requests.post(url_api, data=payload, timeout=5)
    except Exception as e:
        print(f"خطأ في إرسال التنبيه: {e}")

# --- المسارات ---

@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email, password = request.form.get('email'), request.form.get('password')
        user = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
        if user.data:
            session['company_id'] = str(user.data[0]['company_id'])
            return redirect(url_for('dashboard'))
        return "بيانات الدخول خاطئة"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('settings.html')

@app.route('/update_settings', methods=['POST'])
def update_settings():
    if '
