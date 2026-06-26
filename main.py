from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "shimo-secure-2026"

# إعداد Supabase
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key)

# --- دوال مساعدة ---
def get_user_orders():
    if 'user_id' not in session: return []
    res = supabase.table("orders").select("*").eq("user_id", session['user_id']).execute()
    return res.data or []

# --- المسارات ---

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # (هنا يمكنك إضافة منطق التحقق من كلمة السر لاحقاً)
        session['user_id'] = "manager_shimo_id"
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    orders = get_user_orders()
    today = datetime.now().strftime('%Y-%m-%d')
    daily_sales = sum(float(o.get('total_price', 0)) for o in orders if o.get('created_at', '').startswith(today))
    return render_template('dashboard.html', daily_sales=daily_sales, order_count=len(orders))

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        # منطق إضافة طلب جديد (سيتم ربطه بالـ HTML لاحقاً)
        return redirect(url_for('orders'))
    return render_template('orders.html', orders=get_user_orders())

@app.route('/stats')
def stats():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('stats.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('settings.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
