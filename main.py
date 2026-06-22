import os
from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from datetime import datetime

app = Flask(__name__, template_folder='templates')
app.secret_key = 'chaima_secure_2026'

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# صفحة تسجيل الدخول
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        response = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
        if response.data:
            session['user'] = username
            return redirect(url_for('dashboard'))
    return render_template('login.html')

# لوحة التحكم (عرض + إضافة + حساب المجموع)
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    today = datetime.now().strftime('%Y-%m-%d')
    # جلب الطلبات
    orders = supabase.table("orders").select("*").execute()
    # حساب المجموع
    total_today = sum(int(item['price']) for item in orders.data)
    
    return render_template('users.html', orders=orders.data, total=total_today)

# إضافة طلب
@app.route('/add', methods=['POST'])
def add_order():
    name = request.form.get('product_name')
    price = request.form.get('price')
    supabase.table("orders").insert({"product_name": name, "price": price}).execute()
    return redirect(url_for('dashboard'))

# حذف طلب
@app.route('/delete/<int:order_id>')
def delete_order(order_id):
    supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
