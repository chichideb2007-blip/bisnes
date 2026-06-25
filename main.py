import os
from flask import Flask, render_template, request, redirect, session, flash
from supabase import create_client

app = Flask(__name__)
# مفتاح سري لتشفير الجلسات (مهم جداً لعمل الموقع)
app.secret_key = 'shimo_2026_secure_key'

# إعداد Supabase مع فحص لتجنب الانهيار إذا لم تكن البيانات موجودة
url = os.environ.get('SUPABASE_URL', '')
key = os.environ.get('SUPABASE_KEY', '')
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
        
        # تخزين المستخدم في الجلسة للانتقال للوحة التحكم
        if user and email:
            session['user'] = user
            return redirect('/dashboard')
        else:
            return "خطأ: يرجى ملء اسم المستخدم والبريد الإلكتروني!", 400
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    
    products = []
    orders = []
    
    # جلب البيانات من Supabase
    if supabase:
        try:
            products = supabase.table("products").select("*").execute().data
            orders = supabase.table("orders").select("*").execute().data
        except Exception as e:
            print(f"Database Error: {e}")
            
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
    except Exception as e:
        print(f"Add Product Error: {e}")
        
    return redirect('/dashboard')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
