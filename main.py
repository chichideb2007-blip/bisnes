from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from google import genai
import os

app = Flask(__name__)
# تأكدي من ضبط SECRET_KEY في إعدادات Render
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")
app.permanent_session_lifetime = 3600  # الجلسة ستدوم لمدة ساعة

# إعداد الاتصال
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.before_request
def check_session():
    allowed_routes = ['login', 'register', 'static']
    if request.endpoint not in allowed_routes and 'company_id' not in session:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        res = supabase.table("companies").select("*").eq("email", email).execute()
        if res.data and res.data[0]['password'] == password:
            session.permanent = True
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
def dashboard():
    return render_template('dashboard.html')

@app.route('/products', methods=['GET', 'POST'])
def products():
    company_id = session.get('company_id')
    if company_id is None: return redirect(url_for('login'))

    if request.method == 'POST':
        data = {
            "company_id": int(company_id),
            "company_id_text": str(company_id),
            "name": request.form.get('name', 'منتج بدون اسم'),
            "quantity": int(request.form.get('quantity') or 0),
            "price": float(request.form.get('price') or 0.0)
        }
        try:
            supabase.table("inventory").insert(data).execute()
        except Exception as e:
            print("INSERT PRODUCT ERROR:", str(e))
        return redirect(url_for('products'))
    
    res = supabase.table("inventory").select("*").eq("company_id", int(company_id)).execute()
    return render_template('products.html', products=res.data or [])

# دالة الطلبيات المكتملة والمدمجة
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    company_id = session.get('company_id')
    if company_id is None: return redirect(url_for('login'))

    if request.method == 'POST':
        data = {
            "company_id": int(company_id),
            "company_id_text": str(company_id),
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('customer_phone'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('total_price') or 0.0),
            "status": "قيد الانتظار"
        }
        try:
            supabase.table("orders").insert(data).execute()
        except Exception as e:
            print("ORDER INSERT ERROR:", str(e))
        return redirect(url_for('orders'))
    
    res = supabase.table("orders").select("*").eq("company_id", int(company_id)).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

@app.route('/stats')
def stats():
    company_id = session.get('company_id')
    if company_id is None: return redirect(url_for('login'))
    res = supabase.table("orders").select("*").eq("company_id", int(company_id)).execute()
    return render_template('stats.html', orders=res.data or [])

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    company_id = session.get('company_id')
    if company_id is None: return redirect(url_for('login'))
    
    if request.method == 'POST':
        supabase.table("companies").update({
            "store_name": request.form.get('store_name'),
            "telegram_token": request.form.get('token'),
            "manager_phone": request.form.get('phone')
        }).eq("id", company_id).execute()
        return redirect(url_for('settings'))
    
    res = supabase.table("companies").select("*").eq("id", company_id).execute()
    settings_data = res.data[0] if res.data else {}
    return render_template('settings.html', settings=settings_data)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
