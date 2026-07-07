import os
from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client

app = Flask(__name__)
# تأكدي من ضبط FLASK_SECRET_KEY في إعدادات Environment في Render
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'shimo-secret-key-2026')

# إعداد Supabase
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key)

# 1. الصفحة الرئيسية
@app.route('/')
def home():
    return redirect(url_for('login'))

# 2. تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user_id'] = 'admin_user'
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# 3. التسجيل (تمت إضافته لحل خطأ BuildError)
@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')

# 4. لوحة التحكم
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# 5. إدارة الطلبيات
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('total_price', 0))
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    res = supabase.table("orders").select("*").execute()
    return render_template('orders_dashboard.html', orders=res.data)

# 6. حذف طلبية
@app.route('/delete_order/<int:order_id>')
def delete_order(order_id):
    supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect(url_for('orders'))

# 7. الإعدادات
@app.route('/settings')
def settings():
    return render_template('settings.html')

# 8. تسجيل الخروج
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
