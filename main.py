from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = "shimo-secure-2026"

# اتصال قاعدة البيانات
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user_id'] = "manager_shimo_id"
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # جلب الطلبات
    res = supabase.table("orders").select("*").eq("user_id", "manager_shimo_id").execute()
    orders = res.data if res.data else []
    
    # جلب الإعدادات
    set_res = supabase.table("settings").select("*").eq("user_id", "manager_shimo_id").maybe_single().execute()
    settings = set_res.data if set_res.data else {"shop_name": "متجري", "primary_color": "#7e22ce"}
    
    return render_template('dashboard.html', orders=orders, settings=settings)

@app.route('/add-order', methods=['POST'])
def add_order():
    data = {
        "user_id": "manager_shimo_id",
        "customer_name": request.form.get('name'),
        "product_name": request.form.get('product'),
        "total_price": float(request.form.get('price', 0)),
        "customer_phone": request.form.get('phone')
    }
    supabase.table("orders").insert(data).execute()
    return redirect(url_for('dashboard'))

@app.route('/update-info', methods=['POST'])
def update_info():
    data = {
        "user_id": "manager_shimo_id",
        "shop_name": request.form.get('shop_name'),
        "primary_color": request.form.get('primary_color')
    }
    supabase.table("settings").upsert(data).execute()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
