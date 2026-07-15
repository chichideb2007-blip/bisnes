from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

# تعريف التطبيق مع تحديد مجلد القوالب
app = Flask(__name__, template_folder='templates')
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

# إعداد Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# 1. الصفحة الرئيسية
@app.route('/')
def home():
    return "الموقع يعمل بنجاح! - <a href='/login'>اذهب لصفحة الدخول</a>"

# 2. تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        res = supabase.table("companies").select("*").eq("email", email).execute()
        if res.data and res.data[0]['password'] == password:
            session['company_id'] = res.data[0]['id']
            return redirect(url_for('dashboard'))
        return "بيانات الدخول خاطئة"
    return render_template('login.html')

# 3. لوحة التحكم
@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

# 4. مسار الطلبيات (المصحح ليتطابق مع customer_phone و total_price)
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'company_id' not in session: return redirect(url_for('login'))
    
    if request.method == 'POST':
        data = {
            "company_id": session['company_id'],
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('phone'), 
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('price') or 0.0) 
        }
        # محاولة الحفظ مع التقاط الخطأ في حال فشله
        try:
            supabase.table("orders").insert(data).execute()
        except Exception as e:
            print(f"خطأ Supabase: {e}") # هذا سيطبع الخطأ في سجلات Render (Logs)
        return redirect(url_for('orders'))
    
    res = supabase.table("orders").select("*").eq("company_id", session['company_id']).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

# 5. مسار المخزون
@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if 'company_id' not in session: return redirect(url_for('
