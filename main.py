from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from collections import defaultdict
from datetime import datetime
from functools import wraps
import os
import time
import requests

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fallback_dev_key")

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- وظيفة إرسال التنبيه ---
def send_telegram_alert(company_code, message):
    res = supabase.table("settings").select("telegram_token, telegram_chat_id").eq("company_code", company_code).execute()
    if res.data:
        token = res.data[0].get('telegram_token')
        chat_id = res.data[0].get('telegram_chat_id')
        if token and chat_id:
            url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
            try:
                requests.get(url)
            except Exception as e:
                print(f"Error sending Telegram alert: {e}")

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        company_code = request.form.get('company_code') 
        if company_code:
            session['company_code'] = company_code
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# --- مسارات الإعدادات ---
@app.route('/settings', methods=['GET'])
@login_required
def settings():
    company_code = session.get('company_code')
    res = supabase.table("settings").select("*").eq("company_code", company_code).execute()
    settings_data = res.data[0] if res.data else {}
    return render_template('settings.html', settings=settings_data)

@app.route('/update_company', methods=['POST'])
@login_required
def update_company():
    company_code = session.get('company_code')
    data = {
        "company_name": request.form.get('company_name'),
        "telegram_token": request.form.get('telegram_token'),
        "telegram_chat_id": request.form.get('chat_id')
    }
    # تم التحديث باستخدام update كما طلبتِ
    supabase.table("settings").update(data).eq("company_code", company_code).execute()
    return redirect(url_for('settings'))

@app.route('/update_color', methods=['POST'])
@login_required
def update_color():
    company_code = session.get('company_code')
    data = {
        "theme_color": request.form.get('theme_color'),
        "company_code": company_code
    }
    supabase.table("settings").upsert(data).execute()
    return redirect(url_for('settings'))

# --- المنتجات ---
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

    res = supabase.table("inventory").select("*").eq("company_code", company_code).execute()
    return render_template('products.html', products=res.data or [])

# --- الطلبات ---
@app.route('/orders', methods=['GET', 'POST'])
@login_required
def orders():
    company_code = session.get('company_code')
    if request.method == 'POST':
        customer_name = request.form.get('customer_name')
        price = request.form.get('price')
        data = {
            "customer_name": customer_name,
            "customer_phone": request.form.get('phone'),
            "product_name": request.form.get('product_name'),
            "total_price": float(price or 0.0),
            "company_code": company_code
        }
        supabase.table("orders").insert(data).execute()
        send_telegram_alert(company_code, f"🔔 طلبية جديدة: {customer_name} | {price} دج")
        return redirect(url_for('orders'))
    
    res = supabase.table("orders").select("*").eq("company_code", company_code).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

@app.route('/stats')
@login_required
def stats():
    company_code = session.get('company_code')
    try:
        res_orders = supabase.table("orders").select("total_price, created_at").eq("company_code", company_code).execute()
        orders = res_orders.data or []
        res_expenses = supabase.table("expenses").select("amount, created_at").eq("company_code", company_code).execute()
        expenses = res_expenses.data or []
        
        daily_data, monthly_data, yearly_data = defaultdict(float), defaultdict(float), defaultdict(float)
        days_order = ["السبت", "الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
        months_order = ["جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان", "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]

        for o in orders:
            if o.get('created_at'):
                dt = datetime.fromisoformat(o['created_at'].replace('Z', '+00:00'))
                price = float(o.get('total_price') or 0)
                day_name = days_order[dt.weekday()] if dt.weekday() < 7 else "السبت" 
                daily_data[day_name] += price
                monthly_data[months_order[dt.month - 1]] += price
                yearly_data[str(dt.year)] += price

        return render_template('stats.html', total_sales=sum(float(o.get('total_price') or 0) for o in orders),
                               total_expenses=sum(float(e.get('amount') or 0) for e in expenses),
                               total_orders=len(orders), daily=dict(daily_data), monthly=dict(monthly_data), yearly=dict(yearly_data))
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
