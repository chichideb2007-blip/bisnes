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

@app.route('/')
def index():
    return redirect(url_for('orders'))

# --- مسار المنتجات (بدون أي عزل) ---
@app.route('/products', methods=['GET', 'POST'])
def products():
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
            "image_url": image_url
        }
        supabase.table("inventory").insert(data).execute()
        return redirect(url_for('products'))

    res = supabase.table("inventory").select("*").execute()
    return render_template('products.html', products=res.data or [])

# --- مسار الطلبات (الخصم التلقائي بدون عزل) ---
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        product_name = request.form.get('product_name')
        
        # 1. إضافة الطلب
        data = {
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('phone'),
            "product_name": product_name,
            "total_price": float(request.form.get('price', 0.0)),
        }
        supabase.table("orders").insert(data).execute()
        
        # 2. الخصم التلقائي من المخزن (بدون أي شروط)
        product_res = supabase.table("inventory").select("id, quantity").eq("name", product_name).execute()
        
        if product_res.data:
            p_id = product_res.data[0]['id']
            current_qty = int(product_res.data[0]['quantity'])
            
            if current_qty > 0:
                supabase.table("inventory").update({"quantity": current_qty - 1}).eq("id", p_id).execute()
        
        return redirect(url_for('orders'))
    
    res = supabase.table("orders").select("*").execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

# --- مسار الإحصائيات (بدون عزل) ---
@app.route('/stats')
def stats():
    try:
        res_orders = supabase.table("orders").select("total_price").execute()
        orders = res_orders.data or []
        
        res_expenses = supabase.table("expenses").select("amount").execute()
        expenses = res_expenses.data or []
        
        total_sales = sum(float(o.get('total_price', 0) or 0) for o in orders)
        total_expenses = sum(float(e.get('amount', 0) or 0) for e in expenses)
        
        return render_template('stats.html', 
                               total_sales=total_sales, 
                               total_expenses=total_expenses, 
                               total_orders=len(orders))
    except Exception as e:
        return f"خطأ في الإحصائيات: {str(e)}"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('orders'))

if __name__ == '__main__':
    app.run(debug=True)
