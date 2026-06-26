from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from supabase import create_client
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "shimo-secure-2026"

# إعداد Supabase
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key)

# دالة مساعدة لجلب الإعدادات
def get_settings():
    try:
        res = supabase.table("settings").select("*").eq("user_id", "manager_shimo_id").maybe_single().execute()
        return res.data if res.data else {"shop_name": "متجري", "primary_color": "#2563eb"}
    except:
        return {"shop_name": "متجري", "primary_color": "#2563eb"}

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user_id'] = "manager_shimo_id"
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# إضافة المسار المفقود الذي كان يسبب خطأ 500
@app.route('/register')
def register():
    return render_template('register.html') # تأكدي من وجود هذا الملف

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    res = supabase.table("orders").select("*").eq("user_id", session['user_id']).execute()
    orders = res.data or []
    today = datetime.now().strftime('%Y-%m-%d')
    daily_sales = sum(float(o.get('total_price', 0)) for o in orders if o.get('created_at', '').startswith(today))
    order_count = len(orders)
    return render_template('dashboard.html', settings=get_settings(), daily_sales=daily_sales, order_count=order_count)

@app.route('/orders')
def orders():
    if 'user_id' not in session: return redirect(url_for('login'))
    res = supabase.table("orders").select("*").eq("user_id", session['user_id']).execute()
    return render_template('orders.html', orders=res.data or [], settings=get_settings())

@app.route('/stats')
def stats():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('stats.html', settings=get_settings())

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('settings.html', settings=get_settings())

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
