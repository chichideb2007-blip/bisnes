from flask import Flask, render_template, request, redirect, url_for, session, jsonify
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

# --- دالة مساعدة ---
def get_cid():
    return session.get('company_id')

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # في الواقع، ستتحققين هنا من اسم المستخدم وكلمة السر
        session['company_id'] = "1" 
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if not get_cid(): return redirect(url_for('login'))
    return render_template('dashboard.html')

# --- مسار المنتجات (يدعم العزل) ---
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
                supabase.storage.from_("product-images").upload(path=file_path, file=file.read())
                image_url = supabase.storage.from_("product-images").get_public_url(file_path)
        
        data = {
            "name": request.form.get('name'),
            "quantity": int(request.form.get('quantity', 0)),
            "price": float(request.form.get('price', 0.0)),
            "image_url": image_url,
            "company_id": cid # العزل هنا
        }
        supabase.table("inventory").insert(data).execute()
        return redirect(url_for('products'))

    # جلب المنتجات الخاصة بالشركة فقط
    res = supabase.table("inventory").select("*").eq("company_id", cid).execute()
    return render_template('products.html', products=res.data or [])

# --- مسار الطلبات (يدعم العزل) ---
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    cid = get_cid()
    if not cid: return redirect(url_for('login'))

    if request.method == 'POST':
        product_name = request.form.get('product_name')
        data = {
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('phone'),
            "product_name": product_name,
            "total_price": float(request.form.get('price', 0.0)),
            "company_id": cid # العزل هنا
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    res = supabase.table("orders").select("*").eq("company_id", cid).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

# --- مسار الإحصائيات (يدعم العزل) ---
@app.route('/stats')
def show_stats():
    cid = get_cid()
    if not cid: return redirect(url_for('login'))
    
    try:
        # جلب البيانات الخاصة بالشركة فقط
        res_orders = supabase.table("orders").select("total_price, created_at").eq("company_id", cid).execute()
        orders = res_orders.data or []
        
        # (ملاحظة: تأكدي أن جدول expenses يحتوي أيضاً على company_id)
        res_expenses = supabase.table("expenses").select("amount, created_at").eq("company_id", cid).execute()
        expenses = res_expenses.data or []
        
        # ... (بقية منطق الحسابات كما هو) ...
        return render_template('stats.html', total_sales=sum(float(o.get('total_price', 0)) for o in orders), ...)
    except Exception as e:
        return f"خطأ: {str(e)}"

# --- API للذكاء الاصطناعي (يستخدمه الروبوت لاحقاً) ---
@app.route('/api/products/<int:cid>')
def api_get_products(cid):
    # هذا الرابط سيستخدمه Gemini لجلب منتجات شركة معينة
    res = supabase.table("inventory").select("name, price, quantity").eq("company_id", str(cid)).execute()
    return jsonify(res.data)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
