import os
from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client

# إعداد تطبيق Flask
app = Flask(__name__)
app.secret_key = 'your_secret_key_here' # يمكنك تغييرها لأي نص عشوائي

# جلب الإعدادات من Render (تأكدي من إضافتها في Environment Variables)
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

# إنشاء اتصال Supabase بشكل آمن
if not url or not key:
    print("تحذير: لم يتم العثور على SUPABASE_URL أو SUPABASE_KEY في إعدادات البيئة")
    supabase = None
else:
    supabase = create_client(url, key)

# الروابط (Routes)
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # هنا يمكنك إضافة منطق التحقق من اسم المستخدم وكلمة السر
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if supabase is None:
        return "خطأ: قاعدة البيانات غير متصلة (تأكدي من إعدادات Render)", 500
    
    if request.method == 'POST':
        # الحصول على البيانات من النموذج في HTML
        data = {
            "customer_name": request.form.get("customer_name"),
            "product_name": request.form.get("product_name"),
            "total_price": float(request.form.get("total_price", 0)),
            "customer_phone": request.form.get("customer_phone")
        }
        # إرسال البيانات لقاعدة البيانات
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    # عرض الطلبيات
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
    # عند التشغيل محلياً على جهازك
    app.run(debug=True)
