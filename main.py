import os
from flask import Flask, render_template, request, session, redirect
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'shimo_final_2026_fixed'

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key) if url and key else None

@app.route('/')
def index(): return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user'] = request.form.get('username')
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/dashboard', methods=['GET'])
def dashboard():
    if 'user' not in session: return redirect('/login')
    
    orders = []
    total = 0
    if supabase:
        try:
            response = supabase.table("orders").select("*").eq("manager_email", session['user']).execute()
            orders = response.data if response.data else []
            total = sum(float(o.get('price', 0)) for o in orders)
        except Exception: pass
            
    return render_template('dashboard.html', user=session['user'], orders=orders, total=total)

@app.route('/add-order', methods=['POST'])
def add_order():
    if 'user' not in session: return redirect('/login')
    if supabase:
        try:
            supabase.table("orders").insert({
                "customer_name": request.form.get('name'),
                "details": request.form.get('details'),
                "price": float(request.form.get('price', 0)),
                "manager_email": session['user']
            }).execute()
        except Exception: pass
    return redirect('/dashboard')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
