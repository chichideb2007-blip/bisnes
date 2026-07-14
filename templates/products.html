from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from google import genai
import os, uuid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

# إعداد الاتصال بـ Supabase و Gemini
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.before_request
def check_session():
    # السماح بالوصول لهذه الصفحات بدون تسجيل دخول
    if request.endpoint in ['login', 'register', 'static', 'home']: return
    if 'company_id' not in session: return redirect(url_for('login'))

# --- المسارات الرئيسية ---

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

# --- إدارة المنتجات ---
@app.route('/products', methods=['GET', 'POST'])
def products():
    if request.method == 'POST':
        supabase.table("inventory").insert({
            "company_id": session['company_id'], 
            "name": request.form.get('name'),
            "quantity": int(request.form.get('quantity') or 0),
            "price": float(request.form.get('price') or 0)
        }).execute()
        return redirect(url_for('products'))
    
    res = supabase.table("inventory").select("*").eq("company_id", session['company_id']).execute()
    return render_template('products.html', products=res.data or [])

@app.route('/search_products', methods=['GET'])
def search_products():
    query = request.args.get('q', '')
    res = supabase.table("inventory").select("*").eq("company_id", session['company_id']).ilike("name", f"%{query}%").execute()
    return render_template('products.html', products=res.data or [])

@app.route('/delete_product/<int:product_id>')
def delete_product(product_id):
    supabase.table("inventory").delete().eq("id", product_id).execute()
    return redirect(url_for('products'))

# --- إدارة الطلبيات ---
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        supabase.table("orders").insert({
            "company_id": session['company_id'],
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('phone'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('price') or 0),
            "status": "قيد الانتظار"
        }).execute()
        return redirect(url_for('orders'))
    res = supabase.table("orders").select("*").eq("company_id", session['company_id']).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

@app.route('/delete_order/<int:order_id>')
def delete_order(order_id):
    supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect(url_for('orders'))

# --- الإحصائيات والإعدادات ---
@app.route('/stats')
def stats(): return render_template('stats.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    res = supabase.table("companies").select("*").eq("id", session['company_id']).execute()
    return render_template('settings.html', settings=res.data[0] if res.data else {})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/chat', methods=['POST'])
def chat():
    return {"reply": "مرحباً! كيف أساعدك؟"}

if __name__ == '__main__':
    app.run(debug=True)
