from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = "shimo-secure-2026"

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

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

# --- دالة إضافة الطلب (التي كانت ناقصة عندك) ---
@app.route('/add_order', methods=['POST'])
def add_order():
    customer = request.form.get('customer')
    product = request.form.get('product')
    price = request.form.get('price')
    phone = request.form.get('phone')
    
    if customer and product and price and phone:
        supabase.table("orders").insert({
            "customer": customer,
            "product": product,
            "price": float(price),
            "phone": phone
        }).execute()
    return redirect(url_for('orders'))

@app.route('/orders')
def orders():
    # جلب البيانات لعرضها في الجدول
    response = supabase.table("orders").select("*").execute()
    return render_template('orders_dashboard.html', orders=response.data)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    return render_template('settings.html')

@app.route('/stats')
def stats():
    return render_template('stats.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
