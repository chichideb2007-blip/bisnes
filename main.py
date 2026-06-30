from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = "shimo_secure_key_2026"

# إعدادات Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# 1. مسار تسجيل الدخول
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# 2. مسار التسجيل (لحل خطأ BuildError)
@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')

# 3. لوحة التحكم
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# 4. الطلبيات (إضافة وعرض)
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('total_price', 0)),
            "customer_phone": request.form.get('customer_phone')
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    response = supabase.table("orders").select("*").execute()
    return render_template('orders_dashboard.html', orders=response.data)

# 5. الإحصائيات (حساب المجموع بدقة)
@app.route('/stats')
def stats():
    response = supabase.table("orders").select("total_price").execute()
    orders = response.data
    # حساب مجموع المبيعات
    daily_total = sum(float(o.get('total_price', 0)) for o in orders)
    return render_template('stats.html', daily_total=daily_total)

# 6. الإعدادات
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        # منطق حفظ الإعدادات مستقبلاً
        return redirect(url_for('settings'))
    return render_template('settings.html')

# 7. تسجيل الخروج
@app.route('/logout')
def logout():
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
