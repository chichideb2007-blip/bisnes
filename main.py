from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here' # ديري أي كلمة سر تحبيها

# ربط سوبابايس (تأكدي أنك حاطة الـ URL والـ KEY في الـ Environment Variables في Render)
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# صفحة الدخول
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

# لوحة التحكم الرئيسية
@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    # عرض الطلبات
    orders = supabase.table("orders").select("*").eq("company_id", session['company_id']).execute()
    return render_template('users.html', orders=orders.data)

# إدارة المنتجات (المخزن)
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

# تسجيل الخروج
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
