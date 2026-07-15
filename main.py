from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
# ضعي مفتاحاً سرياً عشوائياً هنا
app.secret_key = 'your_secret_key'

# إعداد Supabase (تأكدي أن هذه القيم موجودة في إعدادات Render)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# مسار الصفحة الرئيسية
@app.route('/')
def home():
    return redirect(url_for('login'))

# مسار تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        # تحقق من قاعدة البيانات
        res = supabase.table("companies").select("*").eq("email", email).execute()
        if res.data and res.data[0]['password'] == password:
            session['company_id'] = res.data[0]['id']
            return redirect(url_for('dashboard'))
        return "خطأ في بيانات الدخول"
    return render_template('login.html')

# مسار لوحة التحكم
@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

# مسار المنتجات (المخزون)
@app.route('/products', methods=['GET', 'POST'])
def products():
    if 'company_id' not in session: return redirect(url_for('login'))
    
    if request.method == 'POST':
        data = {
            "company_id": session['company_id'],
            "name": request.form.get('name'),
            "quantity": int(request.form.get('quantity') or 0),
            "price": float(request.form.get('price') or 0.0)
        }
        supabase.table("inventory").insert(data).execute()
        return redirect(url_for('products'))
    
    res = supabase.table("inventory").select("*").eq("company_id", session['company_id']).execute()
    return render_template('products.html', products=res.data or [])

if __name__ == '__main__':
    app.run(debug=True)
