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

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        # إضافة طلبيات جديدة
        data = {
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('customer_phone'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('total_price')),
            "created_at": datetime.now().isoformat()
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    response = supabase.table("orders").select("*").execute()
    orders_data = response.data
    total_sales = sum(float(order.get('total_price', 0)) for order in orders_data)
    return render_template('orders_dashboard.html', orders=orders_data, total=total_sales)

@app.route('/stats')
def stats():
    response = supabase.table("orders").select("*").execute()
    orders_data = response.data
    
    # تصنيف البيانات حسب الأيام، الأشهر، والسنوات
    daily_sales = defaultdict(float)
    monthly_sales = defaultdict(float)
    yearly_sales = defaultdict(float)
    
    for order in orders_data:
        date = datetime.fromisoformat(order.get('created_at', '').replace('Z', ''))
        day_name = date.strftime('%A') # السبت، الأحد...
        month_name = date.strftime('%B') # جانفي، فيفري...
        year = str(date.year)
        
        price = float(order.get('total_price', 0))
        daily_sales[day_name] += price
        monthly_sales[month_name] += price
        yearly_sales[year] += price
        
    return render_template('stats.html', 
                           daily=dict(daily_sales), 
                           monthly=dict(monthly_sales), 
                           yearly=dict(yearly_sales))

# ... (باقي المسارات login, register, delete_order, logout كما هي)
