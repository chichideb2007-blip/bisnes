from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

# تعريف التطبيق مع تحديد مجلد القوالب
app = Flask(__name__, template_folder='templates')
# تأكدي من ضبط SECRET_KEY في إعدادات البيئة في Render
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

# إعداد Supabase باستخدام متغيرات البيئة
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# 1. مسار الصفحة الرئيسية
@app.route('/')
def home():
    return "الموقع يعمل بنجاح! - <a href='/login'>اذهب لصفحة الدخول</a>"

# 2. مسار تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request
