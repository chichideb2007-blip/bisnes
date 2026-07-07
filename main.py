import os
from flask import Flask, render_template, request, redirect, url_for, flash
from supabase import create_client, Client
from dotenv import load_dotenv

# تحميل متغيرات البيئة من ملف .env (للتطوير المحلي)
load_dotenv()

app = Flask(__name__)
app.secret_key = 'your_secret_key_here' # غيريها لشيء سري

# جلب الإعدادات من Render (تأكدي من إضافتها في إعدادات Render)
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

# التحقق من وجود الإعدادات لمنع توقف السيرفر
if not url or not key:
    print("خطأ: يرجى التأكد من إضافة SUPABASE_URL و SUPABASE_KEY في إعدادات Render")
    supabase = None
else:
    supabase = create_client(url, key)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # هنا ستضعين كود التحقق من Supabase لاحقاً
        # حالياً نقوم بإعادة التوجيه للوحة التحكم مباشرة للتجربة
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if not supabase:
        return "قاعدة البيانات غير متصلة", 500
    
    if request.method == 'POST':
        # كود إضافة طلبية جديد
        data = {
            "customer_name": request.form.get("customer_name"),
            "product_name": request.form.get("product_name"),
            "total_price": float(request.form.get("total_price", 0)),
            "customer_phone": request.form.get("customer_phone")
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    # جلب الطلبيات
    response = supabase.table("orders").select("*").execute()
    return render_template('orders_dashboard.html', orders=response.data)

@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/stats')
def stats():
    return render_template('stats.html')

if __name__ == '__main__':
    app.run(debug=True)
