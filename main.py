from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = 'secret_key_123'

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/')
def index():
    return "الموقع يعمل بنجاح!"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['company_id'] = "1"
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        data = {"customer_name": request.form.get('customer_name'), "company_id": "1"}
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    res = supabase.table("orders").select("*").execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

# --- هذا هو المسار الذي كان مفقوداً أو خاطئاً ---
@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if request.method == 'POST':
        data = {
            "name": request.form.get('name'),
            "quantity": request.form.get('quantity'),
            "price": request.form.get('price'),
            "company_id": "1"
        }
        supabase.table("inventory").insert(data).execute()
        return redirect(url_for('inventory'))
    
    res = supabase.table("inventory").select("*").execute()
    return render_template('inventory.html', items=res.data or [])

if __name__ == '__main__':
    app.run(debug=True)
