from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client
import os
from datetime import datetime
from collections import defaultdict

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'your_secret_key'

# إعداد Supabase
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
    if request.method == 'POST':
        data = {
            "customer_name": request.form.get("customer_name"),
            "customer_phone": request.form.get("customer_phone"),
            "product_name": request.form.get("product_name"),
            "total_price": float(request.form.get("total_price", 0)),
            "created_at": datetime.now().isoformat()
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))

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
    orders = response.data
    
    # قوالب بيانات ثابتة (لضمان ظهور كل الأيام/الشهور)
    daily = {day: 0 for day in ['السبت', 'الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة']}
    monthly = {month: 0 for month in ['جانفي', 'فيفري', 'مارس', 'أفريل', 'ماي', 'جوان', 'جويلية', 'أوت', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']}
    yearly = {str(year): 0 for year in range(2026, 2030)}
    
    days_map = {'Monday': 'الاثنين', 'Tuesday': 'الثلاثاء', 'Wednesday': 'الأربعاء', 'Thursday': 'الخميس', 'Friday': 'الجمعة', 'Saturday': 'السبت', 'Sunday': 'الأحد'}
    months_map = {'January': 'جانفي', 'February': 'فيفري', 'March': 'مارس', 'April': 'أفريل', 'May': 'ماي', 'June': 'جوان', 'July': 'جويلية', 'August': 'أوت', 'September': 'سبتمبر', 'October': 'أكتوبر', 'November': 'نوفمبر', 'December': 'ديسمبر'}

    for order in orders:
        created_at = order.get('created_at', datetime.now().isoformat())
        dt = datetime.strptime(created_at[:10], '%Y-%m-%d')
        
        day_name = days_map.get(dt.strftime('%A'))
        month_name = months_map.get(dt.strftime('%B'))
        year_name = str(dt.year)
        
        if day_name in daily: daily[day_name] += float(order.get('total_price', 0))
        if month_name in monthly: monthly[month_name] += float(order.get('total_price', 0))
        if year_name in yearly: yearly[year_name] += float(order.get('total_price', 0))
        
    return render_template('stats.html', daily=daily, monthly=monthly, yearly=yearly)

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
