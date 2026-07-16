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

# دالة لجلب معرف الشركة من الجلسة للتحقق من العزل
def get_cid():
    return session.get('company_id')

@app.route('/')
def index():
    return redirect(url_for('login'))

# --- مسار تسجيل الدخول ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # تثبيت الهوية على "1" ليتوافق مع بياناتك الحالية
        session['company_id'] = "1" 
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# --- لوحة التحكم ---
@app.route('/dashboard')
def dashboard():
    if not get_cid(): 
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# --- مسار المنتجات (العزل + رفع الصور) ---
@app.route('/products', methods=['GET', 'POST'])
def products():
    cid = get_cid()
    if not cid: 
        return redirect(url_for('login'))

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
            "company_id_text": cid 
        }
        try:
            supabase.table("inventory").insert(data).execute()
        except Exception as e:
            return f"حدث خطأ في قاعدة البيانات أثناء إضافة المنتج: {str(e)}"
        return redirect(url_for('products'))

    try:
        res = supabase.table("inventory").select("*").eq("company_id_text", cid).execute()
        products_list = res.data or []
    except Exception as e:
        return f"حدث خطأ أثناء جلب المنتجات: {str(e)}"

    return render_template('products.html', products=products_list)

# --- مسار الطلبات (العزل + رقم الهاتف) ---
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    cid = get_cid()
    if not cid: 
        return redirect(url_for('login'))

    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('phone'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('price', 0.0)),
            "company_id_text": cid
        }
        try:
            supabase.table("orders").insert(data).execute()
        except Exception as e:
            return f"حدث خطأ أثناء إضافة الطلب: {str(e)}"
        return redirect(url_for('orders'))
    
    try:
        res = supabase.table("orders").select("*").eq("company_id_text", cid).execute()
        orders_list = res.data or []
    except Exception as e:
        return f"حدث خطأ أثناء جلب الطلبات: {str(e)}"

    return render_template('orders_dashboard.html', orders=orders_list)

# --- مسار الإحصائيات (المدمج والمصحح بالكامل مع العزل) ---
@app.route('/stats')
def stats():
    cid = get_cid()
    if not cid: 
        return redirect(url_for('login'))
    
    try:
        # 1. جلب الطلبات المفلترة بالشركة الحالية لضمان العزل
        res_orders = supabase.table("orders").select("total_price, created_at").eq("company_id_text", cid).execute()
        orders = res_orders.data or []
        
        # 2. جلب المصاريف المفلترة بالشركة
        try:
            res_expenses = supabase.table("expenses").select("amount, created_at").eq("company_id", cid).execute()
            expenses = res_expenses.data or []
        except Exception:
            # في حال عدم وجود جدول المصاريف أو تسمية العمود مختلفة لتجنب انهيار الصفحة
            expenses = []
        
        # تجهيز البيانات للمنحنيات لتغذية ملف HTML بنجاح
        daily_data = defaultdict(float)
        monthly_data = defaultdict(float)
        yearly_data = defaultdict(float)
        
        days_order = ["السبت", "الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
        months_order = ["جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان", "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]

        for o in orders:
            if o.get('created_at'):
                try:
                    dt = datetime.fromisoformat(o['created_at'].replace('Z', '+00:00'))
                    price = float(o.get('total_price', 0) or 0)
                    
                    day_name = days_order[dt.weekday() if dt.weekday() != 6 else 0]
                    month_name = months_order[dt.month - 1]
                    
                    daily_data[day_name] += price
                    monthly_data[month_name] += price
                    yearly_data[str(dt.year)] += price
                except Exception:
                    # تجاوز أي صيغ تاريخ غير صالحة لضمان استقرار الصفحة
                    pass

        total_sales = sum(float(o.get('total_price', 0) or 0) for o in orders)
        total_expenses = sum(float(e.get('amount', 0) or 0) for e in expenses)
        total_orders = len(orders)

        return render_template('stats.html', 
                               total_sales=total_sales,
                               total_expenses=total_expenses,
                               total_orders=total_orders,
                               daily=dict(daily_data),
                               monthly=dict(monthly_data),
                               yearly=dict(yearly_data))
    except Exception as e:
        return f"حدث خطأ في الإحصائيات: {str(e)}"

# --- مسارات الحذف وتسجيل الخروج ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    cid = get_cid()
    if not cid: return redirect(url_for('login'))
    # أمان إضافي لحذف طلباتك فقط
    supabase.table("orders").delete().eq("id", order_id).eq("company_id_text", cid).execute()
    return redirect(url_for('orders'))

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    cid = get_cid()
    if not cid: return redirect(url_for('login'))
    # أمان إضافي لحذف منتجاتك فقط
    supabase.table("inventory").delete().eq("id", product_id).eq("company_id_text", cid).execute()
    return redirect(url_for('products'))

if __name__ == '__main__':
    app.run(debug=True)
