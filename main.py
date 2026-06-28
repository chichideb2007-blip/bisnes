from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = "shimo-secure-2026"

# إعداد Supabase - تأكدي أن هذه المتغيرات مضبوطة في إعدادات Render
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user'] = 'admin' # تسجيل دخول مبدئي
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    # جلب الإحصائيات (تأكدي من أسماء الجداول في Supabase)
    orders = supabase.table("orders").select("*").execute().data
    return render_template('dashboard.html', orders=orders, total_price=sum(o['total_price'] for o in orders))

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'user' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        # إضافة طلب جديد
        data = {"customer_name": request.form['customer_name'], "product_name": request.form['product_name'], "total_price": float(request.form['total_price'])}
        supabase.table("orders").insert(data).execute()
    orders = supabase.table("orders").select("*").execute().data
    return render_template('orders_dashboard.html', orders=orders, total=sum(o['total_price'] for o in orders))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user' not in session: return redirect(url_for('login'))
    # جلب إعدادات المتجر
    settings_data = supabase.table("settings").select("*").eq("id", 1).execute().data
    s = settings_data[0] if settings_data else {"shop_name": "متجري", "telegram_bot": ""}
    return render_template('settings.html', settings=s)

@app.route('/stats')
def stats():
    return render_template('stats.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
