

from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
import time

app = Flask(__name__)
app.secret_key = 'secret_key_123'

# إعداد Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# دالة باش نجيبو الـ ID تاع الشركة من الـ session
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
        
        # إنشاء معرف فريد للشركة
        new_cid = f"comp_{int(time.time())}" 
        
        # حفظ المعرف في جدول companies
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

# --- مسار المنتجات (العزل بـ company_id_text) ---
@app.route('/products', methods=['GET', 'POST'])
def products():
    cid = get_cid()
    if not cid: return redirect(url_for('login'))

    if request.method == 'POST':
        data = {
            "name": request.form.get('name'),
            "quantity": int(request.form.get('quantity', 0)),
            "price": float(request.form.get('price', 0.0)),
            "company_id_text": cid  # هنا راهي العزلة
        }
        supabase.table("inventory").insert(data).execute()
        return redirect(url_for('products'))

    # الفلترة بـ company_id_text
    res = supabase.table("inventory").select("*").eq("company_id_text", cid).execute()
    return render_template('products.html', products=res.data or [])

# --- مسار الطلبات (العزل بـ company_id_text) ---
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    cid = get_cid()
    if not cid: return redirect(url_for('login'))

    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('price', 0.0)),
            "company_id_text": cid  # هنا راهي العزلة
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    # الفلترة بـ company_id_text
    res = supabase.table("orders").select("*").eq("company_id_text", cid).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

# --- مسار الإحصائيات ---
@app.route('/stats')
def stats():
    if not get_cid(): return redirect(url_for('login'))
    return render_template('stats.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
