from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = "shimo_secure_key_2026"

# إعدادات Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# 1. مسار تسجيل الدخول (معالجة الدخول)
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # التحقق من بيانات الدخول (يمكنك إضافة منطق التحقق هنا لاحقاً)
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# 2. مسار التسجيل (لحل خطأ BuildError)
@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')

# 3. لوحة التحكم الرئيسية
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# 4. مسار الطلبيات
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "product_name": request.form.get('product_name'),
            "total_price": request.form.get('total_price'),
            "customer_phone": request.form.get('customer_phone')
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    # جلب الطلبيات لعرضها
    response = supabase.table("orders").select("*").execute()
    return render_template('orders_dashboard.html', orders=response.data)

# 5. مسار الإحصائيات
@app.route('/stats')
def stats():
    return render_template('stats.html')

# 6. مسار الإعدادات
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    return render_template('settings.html')

# 7. مسار تسجيل الخروج
@app.route('/logout')
def logout():
    return redirect(url_for('login'))

if __name__ == '__main__':
    # استخدام المنفذ الذي يحدده Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
