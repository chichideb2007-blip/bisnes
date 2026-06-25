from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
# مفتاح الجلسة (استخدمي مفتاحاً سرياً قوياً في الواقع)
app.secret_key = "shimo-secure-2026"

# إعداد Supabase (تأكدي من إضافة هذه القيم في إعدادات Render)
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# المسار الرئيسي
@app.route('/')
def home():
    return redirect(url_for('login'))

# مسار تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # أضيفي هنا منطق التحقق من المستخدم من قاعدة البيانات
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# لوحة التحكم الرئيسية
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# مسار الإحصائيات
@app.route('/stats')
def stats():
    return render_template('stats.html')

# مسار الإعدادات
@app.route('/settings')
def settings():
    return render_template('settings.html')

# مسار الطلبيات (عرض البيانات)
@app.route('/orders')
def orders():
    # جلب الطلبيات من Supabase (جدول orders)
    # response = supabase.table("orders").select("*").execute()
    # orders_list = response.data
    return render_template('orders_dashboard.html')

# مسار إضافة طلب جديد
@app.route('/add_order', methods=['POST'])
def add_order():
    customer = request.form.get('customer')
    product = request.form.get('product')
    price = request.form.get('price')
    phone = request.form.get('phone')
    
    # كود إضافة البيانات إلى Supabase
    # supabase.table("orders").insert({"customer": customer, "product": product, "price": price, "phone": phone}).execute()
    
    return redirect(url_for('orders'))

# مسار تسجيل الخروج
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
