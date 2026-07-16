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

# دالة مساعدة للتأكد من تسجيل الدخول
def get_company_id():
    return session.get('company_id')

@app.route('/')
def index():
    return redirect(url_for('login'))

# --- مسار تسجيل الدخول (تم تحديثه) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # في نظام حقيقي نتحقق من البريد وكلمة السر، هنا نعتمد على ما أدخله المستخدم
        # أو يمكنك ربطه بنظام تسجيل دخول Supabase Auth
        session['company_id'] = request.form.get('company_id') 
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# --- مسار لوحة التحكم ---
@app.route('/dashboard')
def dashboard():
    if not get_company_id(): return redirect(url_for('login'))
    return render_template('dashboard.html')

# --- مسار المنتجات (مع عزل كامل) ---
@app.route('/products', methods=['GET', 'POST'])
def products():
    cid = get_company_id()
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
                except Exception as e:
                    print(f"Error uploading image: {e}")
        
        data = {
            "name": request.form.get('name'),
            "quantity": int(request.form.get('quantity', 0)),
            "price": float(request.form.get('price', 0.0)),
            "image_url": image_url,
            "company_id_text": cid # هنا نضمن عدم حدوث خطأ Null
        }
        supabase.table("inventory").insert(data).execute()
        return redirect(url_for('products'))

    # جلب المنتجات الخاصة بهذه الشركة فقط
    res = supabase.table("inventory").select("*").eq("company_id_text", cid).execute()
    return render_template('products.html', products=res.data or [])

# --- مسار الطلبات (مع عزل كامل) ---
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    cid = get_company_id()
    if not cid: return redirect(url_for('login'))

    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('phone'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('price', 0.0)),
            "company_id_text": cid # هنا نضمن عدم حدوث خطأ Null
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    res = supabase.table("orders").select("*").eq("company_id_text", cid).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

# --- مسار الإحصائيات (المصحح ومعزول) ---
@app.route('/stats')
def show_stats():
    cid = get_company_id()
    if not cid: return redirect(url_for('login'))
    
    try:
        # جلب الطلبات والمصروفات لنفس الشركة فقط
        res_orders = supabase.table("orders").select("total_price, created_at").eq("company_id_text", cid).execute()
        orders = res_orders.data or []
        
        # ملاحظة: إذا كان جدول المصروفات لا يحتوي على company_id_text، سيحدث خطأ. 
        # يجب إضافة هذا العمود لجدول expenses أيضاً.
        res_expenses = supabase.table("expenses").select("amount, created_at").eq("company_id_text", cid).execute()
        expenses = res_expenses.data or []
        
        # ... باقي كود الإحصائيات كما هو ...
        return render_template('stats.html', 
                               total_sales=sum(float(o.get('total_price', 0)) for o in orders),
                               total_expenses=sum(float(e.get('amount', 0)) for e in expenses),
                               total_orders=len(orders))
    except Exception as e:
        return f"حدث خطأ: {str(e)}"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
