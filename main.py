from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

# إعداد التطبيق
app = Flask(__name__, template_folder='templates')
# تأكدي من إضافة SECRET_KEY في إعدادات Render (Environment)
app.secret_key = os.environ.get("SECRET_KEY", "super-secret-key-change-this")

# إعداد Supabase مع فحص الأمان
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if url and key:
    supabase = create_client(url, key)
else:
    supabase = None

# 1. الصفحة الرئيسية
@app.route('/')
def home():
    return redirect(url_for('login'))

# 2. صفحة تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if not supabase:
            return "خطأ: قاعدة البيانات غير متصلة (تأكدي من إعدادات البيئة)"
            
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            res = supabase.table("companies").select("*").eq("email", email).execute()
            if res.data and res.data[0].get('password') == password:
                session['company_id'] = res.data[0]['id']
                return redirect(url_for('dashboard'))
            else:
                return "البريد أو كلمة السر غير صحيحة"
        except Exception as e:
            return f"خطأ في الاتصال: {str(e)}"
            
    return render_template('login.html')

# 3. لوحة التحكم
@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# 4. إدارة المنتجات
@app.route('/products', methods=['GET', 'POST'])
def products():
    if 'company_id' not in session: 
        return redirect(url_for('login'))
    
    company_id = session['company_id']
    if request.method == 'POST':
        data = {
            "company_id": int(company_id),
            "name": request.form.get('name'),
            "quantity": int(request.form.get('quantity') or 0),
            "price": float(request.form.get('price') or 0.0)
        }
        if supabase:
            supabase.table("inventory").insert(data).execute()
        return redirect(url_for('products'))
    
    res = []
    if supabase:
        res = supabase.table("inventory").select("*").eq("company_id", int(company_id)).execute()
        res = res.data or []
        
    return render_template('products.html', products=res)

# 5. تسجيل الخروج
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run()
