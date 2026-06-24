import os
from flask import Flask, render_template, request, session, redirect
from supabase import create_client

app = Flask(__name__)
# مفتاح سري للجلسات
app.secret_key = 'shimo_final_2026_secure'

# إعداد Supabase مع حماية إذا كانت المفاتيح مفقودة
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key) if url and key else None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    # تخزين اسم المستخدم في الجلسة
    session['user'] = request.form.get('username')
    return redirect('/dashboard')

@app.route('/dashboard')
def dashboard():
    # الحماية: التأكد من وجود جلسة
    if 'user' not in session: 
        return redirect('/')
    
    orders = []
    total = 0
    
    # محاولة جلب الطلبات من Supabase
    if supabase:
        try:
            # جلب الطلبات الخاصة بهذا المستخدم فقط
            response = supabase.table("orders").select("*").eq("manager_email", session.get('user')).execute()
            orders = response.data if response.data else []
            # حساب الإجمالي
            total = sum(float(o.get('price', 0)) for o in orders)
        except Exception as e:
            print(f"Error connecting to DB: {e}")
            
    return render_template('dashboard.html', user=session['user'], orders=orders, total=total)

@app.route('/add-order', methods=['POST'])
def add_order():
    if 'user' not in session: 
        return redirect('/')
        
    if supabase:
        try:
            # إدراج طلب جديد
            supabase.table("orders").insert({
                "customer_name": request.form.get('name'),
                "details": request.form.get('details'),
                "price": float(request.form.get('price', 0)),
                "manager_email": session.get('user')
            }).execute()
        except Exception as e:
            print(f"Error adding order: {e}")
            
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
