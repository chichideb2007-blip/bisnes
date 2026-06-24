import os
from flask import Flask, render_template, request, redirect, session
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'shimo_final_fix_2026'

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key) if url and key else None

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # نستخدم 'username' كما في نموذج الـ HTML
        session['user'] = request.form.get('username')
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if supabase:
            supabase.table("managers").insert({"email": email, "password": password}).execute()
        return redirect('/login')
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/login')
    # تأمين جلب البيانات
    try:
        response = supabase.table("orders").select("*").eq("manager_email", session['user']).execute()
        orders = response.data if response.data else []
    except:
        orders = []
    
    total_today = sum(float(o.get('price', 0)) for o in orders)
    return render_template('dashboard.html', total_today=total_today, orders=orders)

@app.route('/orders')
def manage_orders():
    if 'user' not in session: return redirect('/login')
    try:
        response = supabase.table("orders").select("*").eq("manager_email", session['user']).execute()
        orders = response.data if response.data else []
    except:
        orders = []
    return render_template('orders_dashboard.html', orders=orders)

@app.route('/add-order', methods=['POST'])
def add_order():
    if 'user' not in session: return redirect('/login')
    supabase.table("orders").insert({
        "customer_name": request.form.get('name'),
        "order_details": request.form.get('details'),
        "price": float(request.form.get('price', 0)),
        "manager_email": session['user']
    }).execute()
    return redirect('/orders')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
