from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
import requests
from datetime import datetime
import json
import uuid 

# --- هذا السطر هو الأهم، يجب أن يكون قبل أي مسار ---
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- الآن تأتي الدوال (مثل إرسال التليجرام) ---
def send_telegram_notification(comp_id, order_details):
    # ... (كود التليجرام الخاص بك) ...
    pass

# --- أخيراً تأتي المسارات (Routes) ---
@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # ... (كود اللوجين الخاص بك) ...
    pass

# ... ضعي هنا بقية المسارات التي أرسلتِها في رسالتك الأخيرة (products, search, delete) ...

if __name__ == '__main__':
    app.run(debug=True)
