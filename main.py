from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client
import os
from datetime import datetime
from collections import defaultdict

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'your_secret_key'

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- المسارات ---

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    # عند إضافة طلبية جديدة (POST)
    if request.method == 'POST':
        data = {
            "customer_name": request.form.get("customer_name"),
            "customer_phone": request.form.get("customer_phone"),
            "product_name": request.form.get("product_name"),
            "total_price": float(request.form.get("total_price", 0))
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))

    # جلب البيانات للعرض
    response = supabase.table("orders").select("*").execute()
    orders_data = response.data
    total_sales = sum(float(order.get('total_price', 0)) for order in orders_data)
    
    return render_template('orders_dashboard.html', orders=orders_data, total=total_sales)

@app.route('/delete_order', methods=['POST'])
def delete_order():
    order_id = request.form.get('order_id')
    if order_id:
        supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect(url_for('orders'))

@app.route('/stats')
def stats():
    response = supabase.table("orders").select("*").execute()
    orders_data = response.data
    
    # تحضير بيانات المنحنيات (تجميع حسب التاريخ)
    # هذا المنطق يفترض وجود حقل 'created_at' في قاعدة البيانات
    daily_sales = defaultdict(float)
    monthly_sales = defaultdict(float)
    yearly_sales = defaultdict(float)
    
    for order in orders_data:
        date_str = order.get('created_at', datetime.now().isoformat())[:10]
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        
        daily_sales[date_str] += float(order.get('total_price', 0))
        monthly_sales[date_obj.strftime('%m-%Y')] += float(order.get('total_price', 0))
        yearly_sales[date_obj.strftime('%Y')] += float(order.get('total_price', 0))
    
    return render_template('stats.html', 
                           daily=dict(daily_sales), 
                           monthly=dict(monthly_sales), 
                           yearly=dict(yearly_sales))

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/logout')
def logout():
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
