import os
from flask import Flask, render_template, request, redirect, session
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'your-secret-key' # غيريه لأي كلمة سر خاصة بكِ

# إعداد الاتصال بـ Supabase
supabase = create_client(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_KEY'))

# --- صفحة الدخول ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = supabase.table("users").select("*").eq("username", username).execute()
        if user.data and user.data[0]['password'] == password:
            session['user'] = user.data[0]['id']
            return redirect('/dashboard')
        error = "خطأ في اسم المستخدم أو كلمة السر"
    return render_template('login.html', error=error)

# --- لوحة التحكم (عرض الطلبات + الإحصائيات + إضافة طلب) ---
@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/login')
    orders = supabase.table("orders").select("*").execute().data
    total_sales = sum(float(o['price']) for o in orders)
    return render_template('dashboard.html', orders=orders, total_sales=total_sales)

# --- دالة إضافة طلب جديد ---
@app.route('/add-order', methods=['POST'])
def add_order():
    if 'user' not in session: return redirect('/login')
    data = {
        "customer_name": request.form.get('customer_name'),
        "product_name": request.form.get('product_name'),
        "price": float(request.form.get('price'))
    }
    supabase.table("orders").insert(data).execute()
    return redirect('/dashboard')

# --- دالة حذف الطلب ---
@app.route('/delete-order/<int:order_id>')
def delete_order(order_id):
    supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect('/dashboard')

# --- تسجيل الخروج ---
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
