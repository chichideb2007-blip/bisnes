from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client
import os

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'your_secret_key'

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- المسارات (Routes) ---

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
    # جلب البيانات
    response = supabase.table("orders").select("*").execute()
    orders_data = response.data
    
    # حساب المجموع الكلي
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
    
    # حساب المجموع لعرضه في الإحصائيات
    total_sales = sum(float(order.get('total_price', 0)) for order in orders_data)
    
    # تجهيز قائمة الأسعار للرسوم البيانية (Chart.js)
    prices = [float(order.get('total_price', 0)) for order in orders_data]
    
    return render_template('stats.html', total=total_sales, prices=prices, orders=orders_data)

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
