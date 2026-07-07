import os
from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client

app = Flask(__name__)
# ضروري جداً لتشغيل الجلسات (Sessions)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'my-super-secret-key-123')

# إعداد Supabase
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')

# إنشاء العميل فقط إذا كانت الإعدادات موجودة
supabase = create_client(url, key) if url and key else None

# 1. المسار الافتراضي
@app.route('/')
def home():
    return redirect(url_for('login'))

# 2. تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user_id'] = 'admin'
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# 3. صفحة التسجيل (تم إضافتها لمنع خطأ BuildError)
@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')

# 4. لوحة التحكم
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# 5. الطلبيات
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if not supabase: return "خطأ: قاعدة البيانات غير متصلة"
    
    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('total_price', 0))
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    response = supabase.table("orders").select("*").execute()
    return render_template('orders_dashboard.html', orders=response.data)

# 6. حذف طلبية
@app.route('/delete_order/<int:order_id>')
def delete_order(order_id):
    if supabase:
        supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect(url_for('orders'))

# 7. الإعدادات
@app.route('/settings')
def settings():
    return render_template('settings.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
