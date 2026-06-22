 import os
from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client

# 1. إعداد التطبيق
app = Flask(__name__)
app.secret_key = 'chaima_secret_key_2026' # غيريها بكلمة سر خاصة بيك

# 2. ربط سوبابايس (تأكدي أنك حاطة المتغيرات في Render)
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- كود تسجيل الدخول ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
        if user.data:
            session['user'] = username
            session['company_id'] = user.data[0]['company_id']
            return redirect(url_for('dashboard'))
    return render_template('login.html')

# --- كود لوحة التحكم (الطلبات) ---
@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    orders = supabase.table("orders").select("*").eq("company_id", session['company_id']).execute()
    return render_template('users.html', orders=orders.data)

# --- كود إدارة المنتجات (المخزن) ---
@app.route('/products')
def get_products():
    if 'user' not in session: return redirect(url_for('login'))
    products = supabase.table("products").select("*").eq("company_id", session['company_id']).execute()
    return render_template('products.html', products=products.data)

@app.route('/add_product', methods=['POST'])
def add_product():
    if 'user' not in session: return "Unauthorized", 401
    name = request.form.get('name')
    price = request.form.get('price')
    quantity = request.form.get('quantity')
    
    supabase.table("products").insert({
        "company_id": session['company_id'],
        "name": name,
        "price": float(price),
        "quantity": int(quantity)
    }).execute()
    return redirect(url_for('get_products'))

# --- تسجيل الخروج ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# 3. تشغيل التطبيق (مع تصحيح مشكلة الـ Port)
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
