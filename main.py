from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = "shimo-secure-2026"

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- دالة الإعدادات ---
def get_settings():
    try:
        res = supabase.table("settings").select("*").eq("user_id", "manager_shimo_id").maybe_single().execute()
        return res.data if res.data else {"shop_name": "متجري", "primary_color": "#7e22ce"}
    except:
        return {"shop_name": "متجري", "primary_color": "#7e22ce"}

# --- المسارات ---

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
    return render_template('dashboard.html', settings=get_settings())

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('total_price', 0)),
            "customer_phone": request.form.get('customer_phone'),
            "user_id": session['user_id']
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    res = supabase.table("orders").select("*").eq("user_id", session['user_id']).execute()
    return render_template('orders_dashboard.html', orders=res.data or [], settings=get_settings())

@app.route('/delete/<int:id>')
def delete_order(id):
    supabase.table("orders").delete().eq("id", id).execute()
    return redirect(url_for('orders'))

@app.route('/stats')
def stats():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('stats.html', settings=get_settings())

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        new_settings = {
            "shop_name": request.form.get('shop_name'),
            "primary_color": request.form.get('primary_color'),
            "user_id": "manager_shimo_id"
        }
        supabase.table("settings").upsert(new_settings).execute()
        return redirect(url_for('settings'))
    return render_template('settings.html', settings=get_settings())

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
