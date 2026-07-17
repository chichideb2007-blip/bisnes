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

def get_cid():
    return session.get('company_id')

@app.route('/')
def index():
    return redirect(url_for('login'))

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

# --- مسار المنتجات ---
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
    return render_template('products.html', products=res.data or [])

# --- مسار الطلبات (مع دمج الأتمتة الذكية) ---
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    cid = get_cid()
    if not cid: return redirect(url_for('login'))

    if request.method == 'POST':
        product_name = request.form.get('product_name')
        price = float(request.form.get('price', 0.0))
        
        # 1. إضافة الطلبية
        data = {
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('phone'),
            "product_name": product_name,
            "total_price": price,
            "company_id_text": str(cid)
        }
        supabase.table("orders").insert(data).execute()
        
        # 2. "ذكاء النظام": خصم الكمية من المخزن
        product = supabase.table("inventory").select("id, quantity").eq("name", product_name).eq("company_id_text", str(cid)).execute()
        if product.data:
            p_id = product.data[0]['id']
            new_qty = max(0, product.data[0]['quantity'] - 1)
            supabase.table("inventory").update({"quantity": new_qty}).eq("id", p_id).execute()
            
        return redirect(url_for('orders'))
    
    res = supabase.table("orders").select("*").eq("company_id_text", str(cid)).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

# --- مسار الإحصائيات ---
@app.route('/stats')
def stats():
    cid = get_cid()
    if not cid: return redirect(url_for('login'))
    
    try:
        res_orders = supabase.table("orders").select("total_price, created_at").eq("company_id_text", str(cid)).execute()
        orders = res_orders.data or []
        
        # المصاريف
        res_expenses = supabase.table("expenses").select("amount").eq("company_id", str(cid)).execute()
        expenses = res_expenses.data or []
        
        daily_data = defaultdict(float)
        # المنطق الخاص بالتواريخ
        for o in orders:
            if o.get('created_at'):
                try:
                    dt = datetime.fromisoformat(o['created_at'].replace('Z', '+00:00'))
                    price = float(o.get('total_price', 0) or 0)
                    daily_data[dt.strftime("%A")] += price
                except: pass

        return render_template('stats.html', 
                               total_sales=sum(float(o.get('total_price', 0) or 0) for o in orders),
                               total_expenses=sum(float(e.get('amount', 0) or 0) for e in expenses),
                               total_orders=len(orders),
                               daily=dict(daily_data))
    except Exception as e:
        return f"خطأ: {str(e)}"

# --- الحذف ---
@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    cid = get_cid()
    if not cid: return redirect(url_for('login'))
    supabase.table("orders").delete().eq("id", order_id).eq("company_id_text", str(cid)).execute()
    return redirect(url_for('orders'))

if __name__ == '__main__':
    app.run(debug=True)
