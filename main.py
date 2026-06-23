import os
from flask import Flask, render_template, request, redirect, session, flash
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
        return redirect('/orders')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

@app.route('/orders')
def manage_orders():
    if 'user' not in session: return redirect('/login')
    orders = supabase.table("orders").select("*").order("id", desc=True).execute().data if supabase else []
    return render_template('orders_dashboard.html', orders=orders)

@app.route('/add-order', methods=['POST'])
def add_order():
    if supabase:
        supabase.table("orders").insert({
            "customer_name": request.form.get('name'),
            "order_details": request.form.get('details'),
            "price": float(request.form.get('price', 0)),
            "status": "جديد"
        }).execute()
    return redirect('/orders')

@app.route('/delete-order/<int:order_id>')
def delete_order(order_id):
    if supabase: supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect('/orders')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
