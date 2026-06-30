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
    return render_template('login.html')

# 2. لوحة التحكم الرئيسية
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# 3. الطلبيات (معالجة الجدولين)
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        # إضافة طلب جديد
        data = {
            "customer_name": request.form.get('customer_name'),
            "product_name": request.form.get('product_name'),
            "total_price": request.form.get('total_price'),
            "customer_phone": request.form.get('customer_phone')
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    # جلب الطلبيات لعرضها في الجدول
    response = supabase.table("orders").select("*").execute()
    return render_template('orders_dashboard.html', orders=response.data)

# 4. الإحصائيات (المنحنيات الثلاثة والمصروف اليومي)
@app.route('/stats')
def stats():
    # المنطق الخاص بجلب البيانات للمنحنيات (أيام، أشهر، سنوات)
    return render_template('stats.html')

# 5. الإعدادات (اسم المتجر، تيلجرام، والألوان)
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        # حفظ الإعدادات والألوان
        return redirect(url_for('settings'))
    return render_template('settings.html')

# 6. زر الخروج
@app.route('/logout')
def logout():
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
