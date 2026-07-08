from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_strong_secret_key' # ضروري لجلسات المستخدمين

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- 1. تسجيل الدخول ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        # التحقق من المستخدم
        user = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
        if user.data:
            session['user_id'] = user.data[0]['id']
            session['company_id'] = user.data[0]['company_id'] # عزل البيانات
            return redirect(url_for('dashboard'))
        return "بيانات الدخول خاطئة"
    return render_template('login.html')

# --- 2. إنشاء حساب ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # أضيفي هنا كود إضافة المستخدم الجديد لـ Supabase
        # مع توليد company_id فريد للشركة الجديدة
        return redirect(url_for('login'))
    return render_template('register.html')

# --- 3. لوحة التحكم (Dashboard) ---
@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

# --- 4. الطلبيات (خاصة بكل شركة) ---
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']

    if request.method == 'POST':
        data = {
            "customer_name": request.form.get("customer_name"),
            "product_name": request.form.get("product_name"),
            "total_price": float(request.form.get("total_price", 0)),
            "company_id": comp_id, # الربط ضروري لمنع التداخل
            "created_at": datetime.now().isoformat()
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))

    # جلب بيانات الشركة الحالية فقط
    orders_data = supabase.table("orders").select("*").eq("company_id", comp_id).execute().data
    return render_template('orders_dashboard.html', orders=orders_data)

# --- 5. الإحصائيات ---
@app.route('/stats')
def stats():
    if 'company_id' not in session: return redirect(url_for('login'))
    # جلب الإحصائيات لنفس الشركة فقط
    return render_template('stats.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
