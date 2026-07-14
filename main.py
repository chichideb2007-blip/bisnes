from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from google import genai
import os, uuid, json

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

# إعداد الاتصال
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.before_request
def check_session():
    if request.endpoint in ['login', 'register', 'static', 'home']: return
    if 'company_id' not in session: return redirect(url_for('login'))

# --- المسارات ---

@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        res = supabase.table("companies").select("*").eq("email", request.form.get('email')).execute()
        if res.data and res.data[0]['password'] == request.form.get('password'):
            session['company_id'] = res.data[0]['id']
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = {
            "email": request.form.get('email'),
            "password": request.form.get('password'),
            "store_name": request.form.get('store_name')
        }
        supabase.table("companies").insert(data).execute()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard(): return render_template('dashboard.html')

@app.route('/products', methods=['GET', 'POST'])
def products():
    if request.method == 'POST':
        # تطابق الأعمدة في جدول inventory
        supabase.table("inventory").insert({
            "company_id": session['company_id'], 
            "name": request.form.get('name'),
            "quantity": int(request.form.get('quantity') or 0),
            "price": float(request.form.get('price') or 0)
        }).execute()
        return redirect(url_for('products'))
    res = supabase.table("inventory").select("*").eq("company_id", session['company_id']).execute()
    return render_template('products.html', products=res.data or [])

@app.route('/delete_product/<int:product_id>')
def delete_product(product_id):
    supabase.table("inventory").delete().eq("id", product_id).execute()
    return redirect(url_for('products'))

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        # تطابق الأعمدة في جدول orders
        supabase.table("orders").insert({
            "company_id": session['company_id'],
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('customer_phone'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('total_price') or 0),
            "status": "قيد الانتظار"
        }).execute()
        return redirect(url_for('orders'))
    res = supabase.table("orders").select("*").eq("company_id", session['company_id']).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

@app.route('/delete_order/<int:order_id>')
def delete_order(order_id):
    supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect(url_for('orders'))

@app.route('/stats')
def stats():
    res = supabase.table("orders").select("*").eq("company_id", session['company_id']).execute()
    orders = res.data or []
    return render_template('stats.html', daily="{}", monthly="{}", yearly="{}")

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    res = supabase.table("companies").select("*").eq("id", session['company_id']).execute()
    return render_template('settings.html', settings=res.data[0] if res.data else {})

@app.route('/update_settings', methods=['POST'])
def update_settings():
    # تطابق الأعمدة في جدول companies
    supabase.table("companies").update({
        "store_name": request.form.get('store_name'),
        "telegram_token": request.form.get('token'),
        "manager_phone": request.form.get('phone') 
    }).eq("id", session['company_id']).execute()
    return redirect(url_for('settings'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
