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

# دالة لجلب معرف الشركة من الجلسة
def get_cid():
    return session.get('company_id')

@app.route('/')
def index():
    return redirect(url_for('login'))

# --- مسار تسجيل الدخول ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['company_id'] = "1" 
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if not get_cid(): return redirect(url_for('login'))
    return render_template('dashboard.html')

# --- مسار المنتجات (عزل صارم) ---
@app.route('/products', methods=['GET', 'POST'])
def products():
    cid = get_cid()
    if not cid: return redirect(url_for('login'))

    if request.method == 'POST':
        image_url = None
        if 'product_image' in request.files:
            file = request.files['product_image']
            if file and file.filename != '':
                unique_filename = f"{int(time.time())}_{file.filename}"
                file_path = f"products/{unique_filename}"
                try:
                    supabase.storage.from_("product-images").upload(path=file_path, file=file.read())
                    image_url = supabase.storage.from_("product-images").get_public_url(file_path)
                except: pass
        
        data = {
            "name": request.form.get('name'),
            "quantity": int(request.form.get('quantity', 0)),
            "price": float(request.form.get('price', 0.0)),
            "image_url": image_url,
            "company_id_text": str(cid) 
        }
        supabase.table("inventory").insert(data).execute()
        return redirect(url_for('products'))

    res = supabase.table("inventory").select("*").eq("company_id_text", str(cid)).execute()
    products_list = [dict(item) for item in res.data] if res.data else []
    return render_template('products.html', products=products_list)

# --- مسار الطلبات (معدل لمنع الخطأ) ---
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    cid = get_cid()
    if not cid: return redirect(url_for('login'))

    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('phone'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('price', 0.0)),
            "company_id_text": str(cid) # تأكيد أن المعرف نص
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    # جلب البيانات مع الفلتر الصارم وتحويلها إلى قائمة قواميس بسيطة
    res = supabase.table("orders").select("*").eq("company_id_text", str(cid)).execute()
    orders_list = [dict(item) for item in res.data] if res.data else []
    return render_template('orders_dashboard.html', orders=orders_list)

# --- مسار الإحصائيات (معدل لمنع الخطأ) ---
@app.route('/stats')
def stats():
    cid = get_cid()
    if not cid: return redirect(url_for('login'))
    
    try:
        # استخدام str(cid) لضمان مطابقة نوع البيانات
        res_orders = supabase.table("orders").select("total_price").eq("company_id_text", str(cid)).execute()
        orders = res_orders.data or []
        
        res_expenses = supabase.table("expenses").select("amount").eq("company_id", str(cid)).execute()
        expenses = res_expenses.data or []
        
        # حساب المجموع كأرقام بسيطة (float)
        total_sales = sum(float(o.get('total_price', 0) or 0) for o in orders)
        total_expenses = sum(float(e.get('amount', 0) or 0) for e in expenses)
        
        return render_template('stats.html', 
                               total_sales=float(total_sales), 
                               total_expenses=float(total_expenses), 
                               total_orders=len(orders))
    except Exception as e:
        return f"خطأ: {str(e)}"

# --- مسارات الحذف (مع العزل) ---
@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    cid = get_cid()
    if not cid: return redirect(url_for('login'))
    supabase.table("orders").delete().eq("id", order_id).eq("company_id_text", str(cid)).execute()
    return redirect(url_for('orders'))

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    cid = get_cid()
    if not cid: return redirect(url_for('login'))
    supabase.table("inventory").delete().eq("id", product_id).eq("company_id_text", str(cid)).execute()
    return redirect(url_for('products'))

if __name__ == '__main__':
    app.run(debug=True)
