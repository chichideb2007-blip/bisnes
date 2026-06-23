import os
from flask import Flask, render_template, request, redirect, session
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'your_secret_key' # استبدليها بكلمة سر قوية

# إعداد الاتصال بـ Supabase
supabase = create_client(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_KEY'))

# --- صفحة الدخول ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # البحث عن المستخدم
        user = supabase.table("users").select("*").eq("username", username).execute()
        if user.data and user.data[0]['password'] == password:
            session['user'] = user.data[0]['id'] # حفظ ID المدير في الجلسة
            return redirect('/dashboard')
        error = "اسم المستخدم أو كلمة المرور غير صحيحة"
    return render_template('login.html', error=error)

# --- لوحة التحكم (عرض الطلبات + الحساب) ---
@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/login')
    
    manager_id = session['user']
    # جلب الطلبات الخاصة بهذا المدير فقط
    orders_response = supabase.table("orders").select("*").eq("manager_id", manager_id).execute()
    orders = orders_response.data
    
    # حساب مجموع الأرباح (total_price)
    total_sales = sum(float(o['total_price'] or 0) for o in orders)
    
    return render_template('dashboard.html', orders=orders, total_sales=total_sales)

# --- إضافة طلب جديد ---
@app.route('/add-order', methods=['POST'])
def add_order():
    if 'user' not in session: return redirect('/login')
    
    data = {
        "customer_name": request.form.get('customer_name'),
        "product_name": request.form.get('product_name'),
        "total_price": float(request.form.get('total_price')),
        "manager_id": session['user'] # ربط الطلب بالمدير المسجل
    }
    
    supabase.table("orders").insert(data).execute()
    return redirect('/dashboard')

# --- حذف طلب ---
@app.route('/delete-order/<int:order_id>')
def delete_order(order_id):
    if 'user' not in session: return redirect('/login')
    supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect('/dashboard')

# --- تسجيل الخروج ---
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
