from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from collections import defaultdict
from datetime import datetime
from functools import wraps
import os
import time
import requests

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fallback_dev_key")

# إعداد Supabase
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(URL, KEY)

# --- دالة تجديد التوكن ---
def refresh_and_get_token():
    try:
        # جلب التوكن من جدول settings (نستخدم company_code للتمييز)
        # ملاحظة: إذا كان التوكن مشتركاً لكل الشركات، يمكنك استخدام قيمة ثابتة
        res = supabase.table("settings").select("instagram_token").eq("company_code", "DEFAULT").single().execute()
        old_token = res.data.get('instagram_token')
        
        if not old_token: return None

        url = f"https://graph.facebook.com/v20.0/oauth/access_token?grant_type=fb_exchange_token&client_id={os.environ.get('APP_ID')}&client_secret={os.environ.get('APP_SECRET')}&fb_exchange_token={old_token}"
        
        res_meta = requests.get(url).json()
        
        if 'access_token' in res_meta:
            new_token = res_meta['access_token']
            supabase.table("settings").update({"instagram_token": new_token}).eq("company_code", "DEFAULT").execute()
            print("✅ تم تجديد التوكن بنجاح!")
            return new_token
    except Exception as e:
        print(f"❌ خطأ في تجديد التوكن: {e}")
    return None

# استدعاء الدالة عند بداية تشغيل التطبيق (اختياري)
current_token = refresh_and_get_token()

# --- بقية الكود الخاص بك (الدوال الموجودة سابقاً) ---

def send_telegram_alert(company_code, message):
    # ... (نفس الكود الخاص بك)
    pass

def send_telegram_alert_by_token(token, chat_id, message):
    # ... (نفس الكود الخاص بك)
    pass

@app.route('/login', methods=['GET', 'POST'])
def login():
    # ... (نفس الكود الخاص بك)
    pass

# ... ضعي باقي المسارات (Routes) هنا تحت بعضها ...

if __name__ == '__main__':
    app.run(debug=True)
