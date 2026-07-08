from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
from datetime import datetime

app = Flask(__name__)
# مفتاح سري ضروري لتأمين الجلسات (Sessions)
app.secret_key = 'your_super_secret_key'

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- المسارات (Routes) ---

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        # تحقق من بيانات المستخدم
        user = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
        if user.data:
            # تخزين معرف الشركة في الجلسة لعزل البيانات
            session['company_id'] = user.data[0]['company_id']
            return redirect(url_for('dashboard'))
        return "بيانات الدخول خاطئة"
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # أضيفي هنا كود إضافة المستخدم لجدول users
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/orders')
def orders():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    # جلب بيانات الشركة الحالية فقط
    response = supabase.table("orders").select("*").eq("company_id", comp_id).execute()
    return render_template('orders_dashboard.html', orders=response.data)

if __name__ == '__main__':
    app.run(debug=True)
