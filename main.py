from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from supabase import create_client
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "shimo-secure-2026"

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

def get_settings():
    try:
        res = supabase.table("settings").select("*").eq("user_id", "manager_shimo_id").maybe_single().execute()
        return res.data if res.data else {"shop_name": "متجري", "primary_color": "#7e22ce"}
    except:
        return {"shop_name": "متجري", "primary_color": "#7e22ce"}

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
    if 'user_id' not in session: return redirect(url_for('login'))
    
    # جلب البيانات الحقيقية لحساب المبيعات
    orders = supabase.table("orders").select("*").eq("user_id", session['user_id']).execute().data or []
    
    today = datetime.now().strftime('%Y-%m-%d')
    daily_sales = sum(float(o.get('total_price', 0)) for o in orders if o.get('created_at', '').startswith(today))
    
    return render_template('dashboard.html', 
                           settings=get_settings(), 
                           total_sales=daily_sales, 
                           order_count=len(orders))

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('total_price', 0)),
            "customer_phone": request.form.get('customer_phone'),
            "created_at": datetime.now().isoformat(), # ضروري للحسابات
            "user_id": session['user_id']
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    res = supabase.table("orders").select("*").eq("user_id", session['user_id']).execute()
    return render_template('orders_dashboard.html', orders=res.data or [], settings=get_settings())

@app.route('/api/stats')
def api_stats():
    # هذا المسار يرسل البيانات للرسم البياني
    res = supabase.table("orders").select("*").eq("user_id", session['user_id']).execute()
    return jsonify(res.data or [])

@app.route('/stats')
def stats():
    return render_template('stats.html', settings=get_settings())

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        new_settings = {
            "shop_name": request.form.get('shop_name'),
            "telegram_bot": request.form.get('telegram_bot'),
            "primary_color": request.form.get('primary_color'),
            "user_id": "manager_shimo_id"
        }
        supabase.table("settings").upsert(new_settings).execute()
        return redirect(url_for('settings'))
    return render_template('settings.html', settings=get_settings())

@app.route('/delete/<int:id>')
def delete_order(id):
    supabase.table("orders").delete().eq("id", id).execute()
    return redirect(url_for('orders'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
