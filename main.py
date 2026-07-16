from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from collections import defaultdict
from datetime import datetime
import os
import time

app = Flask(__name__)
app.secret_key = 'secret_key_123'

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/')
def index():
    return redirect(url_for('login'))

# --- مسار تسجيل الدخول ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # نضع الـ ID الخاص بالشركة في الجلسة (Session)
        session['company_id'] = request.form.get('company_id')
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# --- مسار لوحة التحكم ---
@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

# --- مسار المنتجات ---
@app.route('/products', methods=['GET', 'POST'])
def products():
    if 'company_id' not in session: return redirect(url_for('login'))
    company_id = session['company_id']

    if request.method == 'POST':
        image_url = None
        # ... كود رفع الصورة ...
        data = {
            "name": request.form.get('name'),
            "quantity": int(request.form.get('quantity', 0)),
            "price": float(request.form.get('price', 0.0)),
            "image_url": image_url,
            "company_id": company_id # الربط بالشركة
        }
        supabase.table("inventory").insert(data).execute()
        return redirect(url_for('products'))

    # جلب منتجات الشركة المسجلة فقط باستخدام العزل
    res = supabase.table("inventory").select("*").eq("company_id", company_id).execute()
    return render_template('products.html', products=res.data or [])

# --- مسار الطلبات ---
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'company_id' not in session: return redirect(url_for('login'))
    company_id = session['company_id']

    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('price', 0.0)),
            "company_id": company_id # الربط بالشركة
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    # جلب الطلبات للشركة المسجلة فقط
    res = supabase.table("orders").select("*").eq("company_id", company_id).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

# --- مسار الإحصائيات ---
@app.route('/stats')
def show_stats():
    if 'company_id' not in session: return redirect(url_for('login'))
    company_id = session['company_id']
    try:
        # جلب البيانات للشركة الحالية فقط
        res_orders = supabase.table("orders").select("total_price, created_at").eq("company_id", company_id).execute()
        orders = res_orders.data or []
        
        # تجهيز البيانات للمنحنيات
        daily_data = defaultdict(float)
        days_order = ["السبت", "الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
        
        for o in orders:
            if o.get('created_at'):
                dt = datetime.fromisoformat(o['created_at'].replace('Z', '+00:00'))
                price = float(o.get('total_price', 0))
                daily_data[days_order[dt.weekday() if dt.weekday() != 6 else 0]] += price
        
        return render_template('stats.html', 
                               total_orders=len(orders), 
                               daily=dict(daily_data))
    except Exception as e:
        return f"حدث خطأ: {str(e)}"

# --- مسارات إضافية ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
