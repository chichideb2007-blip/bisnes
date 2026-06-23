import os
from flask import Flask, render_template, request, redirect, session
from flask_mail import Mail, Message
from supabase import create_client

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')

# الاتصال بـ Supabase
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

mail = Mail(app)

# 1. الصفحة الرئيسية تحول مباشرة لصفحة الدخول
@app.route('/')
def home():
    return redirect('/login')

# 2. تسجيل مستخدم جديد
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = {
            "username": request.form.get('username'),
            "email": request.form.get('email'),
            "password": request.form.get('password')
        }
        supabase.table("users").insert(data).execute()
        return redirect('/login')
    return render_template('login.html', is_register=True)

# 3. تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_response = supabase.table("users").select("*").eq("username", username).execute()
        
        if user_response.data:
            user = user_response.data[0]
            if user['password'] == password and user['email'] == email:
                session['user'] = user['id']
                return redirect('/dashboard')
        
        error = "خطأ: اسم المستخدم أو الإيميل أو كلمة السر غير صحيحة!"
    return render_template('login.html', is_register=False, error=error)

# 4. حفظ الإعدادات
@app.route('/save-settings', methods=['POST'])
def save_settings():
    if 'user' not in session: return redirect('/login')
    data = {
        "manager_id": session['user'],
        "smtp_server": request.form.get('smtp_server'),
        "smtp_port": int(request.form.get('smtp_port')),
        "email_address": request.form.get('email_address'),
        "email_password": request.form.get('email_password')
    }
    supabase.table("manager_settings").upsert(data, on_conflict="manager_id").execute()
    return redirect('/dashboard')

# 5. لوحة التحكم
@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/login')
    return "مرحباً بك في لوحة التحكم!"

# 6. تشغيل السيرفر
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
