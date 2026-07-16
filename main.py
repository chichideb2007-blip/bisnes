from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
import time

app = Flask(__name__)
app.secret_key = 'secret_key_123'

# إعداد Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# دالة لجلب معرف الشركة من الجلسة
def get_cid():
    return session.get('company_id')

@app.route('/')
def index():
    return redirect(url_for('login'))

# --- تسجيل حساب جديد ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        supabase.auth.sign_up({"email": email, "password": password})
        new_cid = f"comp_{int(time.time())}" 
        supabase.table("companies").insert({"email": email, "company_id": new_cid}).execute()
        return redirect(url_for('login'))
    return render_template('register.html')

# --- تسجيل الدخول ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            supabase.auth.sign_in_with_password({"email": email, "password": password})
            res = supabase.table("companies").select("company_id").eq("email", email).execute()
            if res.data:
                session['company_id'] = res.data[0]['company_id']
                return redirect(url_for('dashboard'))
        except:
            return "خطأ في تسجيل الدخول!"
    return render_template('login.html')

# --- لوحة التحكم ---
@app.route('/dashboard')
def dashboard():
    if not get_cid(): return redirect(url_for('login'))
    return render_template('dashboard.html')

# --- مسار المنتجات ---
@app.route('/products', methods=['GET', 'POST'])
def products():
    cid = get_cid()
    if not cid: return redirect(url_for('login'))
