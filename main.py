from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from collections import defaultdict
from datetime import datetime
from functools import wraps
import os
import time

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fallback_dev_key")

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- Decorator لحماية المسارات ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'company_code' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return redirect(url_for('login'))

# --- مسار تسجيل الدخول ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # المستخدم يدخل كود شركته الخاص
        company_code = request.form.get('company_code')
        if company_code:
            session['company_code'] = company_code
            return redirect(url_for('dashboard'))
    return render_template('login.html')

# --- مسار لوحة التحكم ---
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# --- مسار المنتجات ---
@app.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    company_code = session.get('company_code')
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
                except Exception as e:
                    print(f"Error uploading image: {e}")
        
        data = {
            "name": request.form.get('name'),
            "quantity": int(request.form.get('quantity', 0)),
            "price": float(request.form.get('price', 0.0)),
            "image_url": image_url,
            "company_code": company_code
        }
        supabase.table("inventory").insert(data).execute()
        return redirect(url_for('products'))

    # عرض منتجات الشركة الحالية فقط
    res = supabase.table("inventory").select("*").eq("company_code", company_code).execute()
    return render_template('products.html', products=res.data or [])

# --- مسار الطلبات ---
@app.route('/orders', methods=['GET', 'POST'])
@login_required
def orders():
    company_code = session.get('company_code')
    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('phone'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('price', 0.0)),
            "company_code": company_code
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    # عرض طلبات الشركة الحالية فقط
    res = supabase.table("orders").select("*").eq("company_code", company_code).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

# --- مسار الإحصائيات ---
@app.route('/stats')
@login_required
def show_stats():
    company_code = session.get('company_code')
    try:
        # جلب البيانات الخاصة بالشركة فقط
        res_orders = supabase.table("orders").select("total_price, created_at").eq("company_code", company_code).execute()
        orders = res_orders.data or []
        
        res_expenses = supabase.table("expenses").select("amount, created_at").eq("company_code", company_code).execute()
        expenses = res_expenses.data or []
        
        # ... (بقية منطق الحسابات كما هو) ...
        return render_template('stats.html', total_sales=sum(float(o.get('total_price', 0)) for o in orders),
                               total_expenses=sum(float(e.get('amount', 0)) for e in expenses),
                               total_orders=len(orders))
    except Exception as e:
        return f"حدث خطأ: {str(e)}"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/delete_order/<int:order_id>', methods=['POST'])
@login_required
def delete_order(order_id):
    supabase.table("orders").delete().eq("id", order_id).eq("company_code", session.get('company_code')).execute()
    return redirect(url_for('orders'))

@app.route('/delete_product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    supabase.table("inventory").delete().eq("id", product_id).eq("company_code", session.get('company_code')).execute()
    return redirect(url_for('products'))

if __name__ == '__main__':
    app.run(debug=True)
