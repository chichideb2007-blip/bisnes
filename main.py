import os
from flask import Flask, render_template, request, redirect, session, flash
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'shimo_2026_secure'

# إعداد Supabase مع حماية لتجنب الخطأ 500 إذا كانت الإعدادات مفقودة
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key) if url and key else None

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # استقبال البيانات من login.html
        user = request.form.get('username')
        email = request.form.get('email')
        
        # تخزين البيانات في الجلسة للانتقال للوحة التحكم
        if user and email:
            session['user'] = user
            return redirect('/dashboard')
        else:
            flash("يرجى ملء جميع الحقول!")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    
    # محاولة جلب البيانات مع تأمين ضد الانهيار
    products = []
    orders = []
    try:
        if supabase:
            products = supabase.table("products").select("*").execute().data
            orders = supabase.table("orders").select("*").execute().data
    except Exception as e:
        print(f"Error fetching data: {e}")
        
    return render_template('dashboard.html', products=products, orders=orders)

@app.route('/add-product', methods=['POST'])
def add_product():
    if 'user' not in session: return redirect('/login')
    
    try:
        if supabase:
            data = {
                "name": request.form.get('name'),
                "price": float(request.form.get('price', 0)),
                "stock_quantity": int(request.form.get('stock', 0))
            }
            supabase.table("products").insert(data).execute()
            flash("تمت الإضافة بنجاح!")
    except Exception as e:
        flash("خطأ في الاتصال بقاعدة البيانات.")
        
    return redirect('/dashboard')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
