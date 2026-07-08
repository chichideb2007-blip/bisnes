from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
from datetime import datetime

app = Flask(__name__)
# مفتاح سري لتأمين الجلسات (مهم جداً)
app.secret_key = 'my_super_secure_secret_key'

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- نظام الدخول الآمن ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        # التحقق من المستخدم في جدول users
        user = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
        if user.data:
            # تخزين هوية الشركة في الجلسة (العزل يبدأ من هنا)
            session['company_id'] = user.data[0]['company_id']
            return redirect(url_for('dashboard'))
        return "بيانات الدخول خاطئة"
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # أضيفي هنا كود إضافة المستخدم الجديد لجدول users في Supabase
        return redirect(url_for('login'))
    return render_template('register.html')

# --- لوحة التحكم (محمية) ---

@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

# --- إدارة الطلبيات (مع عزل البيانات) ---

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']

    if request.method == 'POST':
        data = {
            "customer_name": request.form.get("customer_name"),
            "product_name": request.form.get("product_name"),
            "total_price": float(request.form.get("total_price", 0)),
            "company_id": comp_id, # ربط الطلبية بشركة المدير تلقائياً
            "created_at": datetime.now().isoformat()
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))

    # جلب طلبات هذه الشركة فقط
    orders_data = supabase.table("orders").select("*").eq("company_id", comp_id).execute().data
    return render_template('orders_dashboard.html', orders=orders_data)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
