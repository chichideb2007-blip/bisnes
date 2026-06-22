import os
from flask import Flask, render_template, request, redirect, session
from supabase import create_client

# --- تهيئة التطبيق ---
app = Flask(__name__)
app.secret_key = 'chaima_pro_2026'

# --- الاتصال بـ Supabase ---
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- المسارات (Routes) ---

@app.route('/')
def index():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        response = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
        if response.data:
            session['user'] = username
            return redirect('/dashboard')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/login')
    # جلب طلبات المدير الحالي فقط
    response = supabase.table("orders").select("*").eq("manager_id", session['user']).execute()
    orders = response.data
    total = sum(float(item.get('total_price', 0)) for item in orders if item.get('total_price'))
    return render_template('users.html', orders=orders, total=total)

@app.route('/add', methods=['POST'])
def add():
    if 'user' not in session: return redirect('/login')
    
    # التقاط البيانات بدقة من الفورم
    data = {
        "customer_name": request.form.get('customer_name'),
        "product_name": request.form.get('product_name'),
        "total_price": request.form.get('total_price'),
        "manager_id": session['user']
    }
    
    # محاولة إضافة البيانات لقاعدة البيانات
    try:
        supabase.table("orders").insert(data).execute()
    except Exception as e:
        print(f"خطأ في الإضافة: {e}")
        
    return redirect('/dashboard')

@app.route('/delete/<int:id>')
def delete(id):
    if 'user' not in session: return redirect('/login')
    supabase.table("orders").delete().eq("id", id).execute()
    return redirect('/dashboard')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
