import os
from flask import Flask, render_template, request, redirect, session, flash
from supabase import create_client

app = Flask(__name__)
# مفتاح سري لتشفير الجلسة
app.secret_key = 'shimo_super_secret_2026'

# إعداد الاتصال بـ Supabase مع حماية من الأخطاء
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key) if url and key else None

# توجيه الصفحة الرئيسية لصفحة تسجيل الدخول
@app.route('/')
def home():
    return redirect('/login')

# نظام تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username')
        if user:
            session['user'] = user
            return redirect('/dashboard')
        flash("يرجى إدخال اسم المستخدم")
    return render_template('login.html')

# لوحة التحكم
@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/login')
    
    products = []
    orders = []
    
    if supabase:
        try:
            # جلب البيانات من الجداول
            products = supabase.table("products").select("*").execute().data
            orders = supabase.table("orders").select("*").execute().data
        except Exception as e:
            print(f"Error: {e}")
            
    return render_template('dashboard.html', products=products, orders=orders)

# إضافة منتج جديد
@app.route('/add-product', methods=['POST'])
def add_product():
    if 'user' not in session: return redirect('/login')
    
    if supabase:
        try:
            name = request.form.get('name')
            price = float(request.form.get('price', 0))
            stock = int(request.form.get('stock', 0))
            
            supabase.table("products").insert({
                "name": name, 
                "price": price, 
                "stock_quantity": stock
            }).execute()
            flash("تم إضافة المنتج بنجاح!")
        except Exception as e:
            flash(f"حدث خطأ أثناء الإضافة: {e}")
            
    return redirect('/dashboard')

# تسجيل الخروج
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
