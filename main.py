import os
from flask import Flask, render_template, request, redirect, session
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'shimo_final_2026_pro'

# إعداد Supabase
url = os.environ.get('SUPABASE_URL', '')
key = os.environ.get('SUPABASE_KEY', '')
supabase = create_client(url, key) if url and key else None

# 1. الصفحة الرئيسية توجه للدخول
@app.route('/')
def home():
    return redirect('/login')

# 2. تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user'] = request.form.get('username')
        return redirect('/dashboard')
    return render_template('login.html')

# 3. إنشاء حساب جديد
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if supabase:
            supabase.table("managers").insert({"email": email, "password": password}).execute()
        return redirect('/login')
    return render_template('register.html')

# 4. لوحة التحكم الرئيسية (الإحصائيات)
@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/login')
    orders = supabase.table("orders").select("*").eq("manager_email", session['user']).execute().data if supabase else []
    total_today = sum(float(o.get('price', 0)) for o in orders)
    return render_template('dashboard.html', total_today=total_today, orders=orders)

# 5. إدارة الطلبات
@app.route('/orders')
def manage_orders():
    if 'user' not in session: return redirect('/login')
    orders = supabase.table("orders").select("*").eq("manager_email", session['user']).execute().data if supabase else []
    return render_template('orders_dashboard.html', orders=orders)

# 6. إضافة طلب
@app.route('/add-order', methods=['POST'])
def add_order():
    if 'user' not in session: return redirect('/login')
    supabase.table("orders").insert({
        "customer_name": request.form.get('name'),
        "order_details": request.form.get('details'),
        "price": float(request.form.get('price', 0)),
        "manager_email": session['user']
    }).execute()
    return redirect('/orders')

# 7. حذف طلب
@app.route('/delete-order/<int:order_id>')
def delete_order(order_id):
    supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect('/orders')

# 8. الإعدادات
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user' not in session: return redirect('/login')
    if request.method == 'POST':
        supabase.table("managers").update({
            "store_name": request.form.get('store_name'),
            "bot_token": request.form.get('bot_token')
        }).eq("email", session['user']).execute()
    return render_template('settings.html')

# 9. تسجيل الخروج
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
