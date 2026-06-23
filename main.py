import os
from flask import Flask, render_template, request, redirect, session, flash
from supabase import create_client

app = Flask(__name__)
# استخدام مفتاح سري بسيط لتجنب خطأ الجلسات
app.secret_key = 'shimo_2026_secure'

# التأكد من وجود المتغيرات لتجنب الانهيار
url = os.environ.get('SUPABASE_URL', '')
key = os.environ.get('SUPABASE_KEY', '')
supabase = create_client(url, key) if url and key else None

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # استخدام الاسم الصحيح للحقل في login.html
        username = request.form.get('username')
        if username:
            session['user'] = username
            return redirect('/dashboard')
        flash("يرجى إدخال اسم المستخدم")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    # إذا كانت قاعدة البيانات غير متصلة، نعرض صفحة فارغة بدل الخطأ
    products = []
    orders = []
    if supabase:
        try:
            products = supabase.table("products").select("*").execute().data
            orders = supabase.table("orders").select("*").execute().data
        except:
            pass
    return render_template('dashboard.html', products=products, orders=orders)

@app.route('/add-product', methods=['POST'])
def add_product():
    if 'user' not in session: return redirect('/login')
    if supabase:
        try:
            data = {
                "name": request.form.get('name'),
                "price": float(request.form.get('price', 0)),
                "stock_quantity": int(request.form.get('stock', 0))
            }
            supabase.table("products").insert(data).execute()
        except:
            flash("خطأ في إضافة المنتج!")
    return redirect('/dashboard')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
