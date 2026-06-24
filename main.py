import os
from flask import Flask, render_template, request, redirect, session
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'shimo_final_2026'

url = os.environ.get('SUPABASE_URL', '')
key = os.environ.get('SUPABASE_KEY', '')
supabase = create_client(url, key) if url and key else None

@app.route('/')
def home(): return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user'] = request.form.get('username')
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/login')
    # جلب الطلبات
    response = supabase.table("orders").select("*").eq("manager_email", session['user']).execute() if supabase else None
    orders = response.data if response else []
    total = sum(float(o.get('price', 0)) for o in orders)
    return render_template('dashboard.html', total=total, orders=orders)

@app.route('/add-order', methods=['POST'])
def add_order():
    if 'user' not in session: return redirect('/login')
    if supabase:
        supabase.table("orders").insert({
            "customer_name": request.form.get('name'),
            "order_details": request.form.get('details'),
            "price": float(request.form.get('price', 0)),
            "manager_email": session.get('user')
        }).execute()
    return redirect('/dashboard')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
