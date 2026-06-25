from flask import Flask, render_template, request, redirect, session, url_for
from supabase import create_client
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "shimo-secure-2026"

# تهيئة Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

def get_user_settings(user_id):
    res = supabase.table("settings").select("*").eq("user_id", user_id).maybe_single().execute()
    if res.data:
        return res.data
    return {"shop_name": "متجري", "bot_token": "", "chat_id": "", "primary_color": "#7e22ce"}

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user_id'] = "manager_shimo_id" # تجربة دخول
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id', 'manager_shimo_id')
    settings = get_user_settings(user_id)
    
    # جلب الطلبات
    res = supabase.table("orders").select("*").eq("user_id", user_id).execute()
    orders = res.data if res.data else []
    
    # قيم افتراضية للمنحنيات (تجنباً للخطأ)
    weekly = [0]*7
    monthly = [0]*12
    yearly = [0]*3
    daily_total = 0
    
    return render_template('dashboard.html', 
                           settings=settings, 
                           orders=orders,
                           weekly_data=weekly,
                           monthly_data=monthly,
                           yearly_data=yearly,
                           daily_total=daily_total)

@app.route('/add-order', methods=['POST'])
def add_order():
    user_id = session.get('user_id', 'manager_shimo_id')
    new_order = {
        "user_id": user_id,
        "customer_name": request.form.get('name'),
        "product_name": request.form.get('product'),
        "total_price": float(request.form.get('price', 0)),
        "customer_phone": request.form.get('phone')
    }
    supabase.table("orders").insert(new_order).execute()
    return redirect(url_for('dashboard'))

@app.route('/update-info', methods=['POST'])
def update_info():
    user_id = session.get('user_id', 'manager_shimo_id')
    data = {
        "user_id": user_id,
        "shop_name": request.form.get('shop_name'),
        "bot_token": request.form.get('bot_token'),
        "chat_id": request.form.get('chat_id'),
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
