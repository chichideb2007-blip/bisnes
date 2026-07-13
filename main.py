from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os, uuid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

# إعداد الاتصال بـ Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

@app.before_request
def check_session():
    allowed_routes = ['login', 'static', 'home']
    if request.endpoint in allowed_routes: return
    if 'company_id' not in session: return redirect(url_for('login'))

@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        res = supabase.table("companies").select("*").eq("email", email).execute()
        if res.data and res.data[0]['password'] == password:
            session['company_id'] = res.data[0]['id']
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard(): return render_template('dashboard.html')

@app.route('/stats')
def stats(): return render_template('stats.html')

@app.route('/search_products', methods=['GET'])
def search_products():
    query = request.args.get('q', '')
    res = supabase.table("inventory").select("*").eq("company_id", session['company_id']).ilike("name", f"%{query}%").execute()
    return render_template('products.html', products=res.data or [])

@app.route('/products', methods=['GET', 'POST'])
def products():
    if request.method == 'POST':
        # (منطق رفع الصورة وحفظ المنتج هنا...)
        # تأكدي أن اسم الـ bucket هو 'product-images'
        return redirect(url_for('products'))
    
    res = supabase.table("inventory").select("*").eq("company_id", session['company_id']).execute()
    return render_template('products.html', products=res.data or [])

@app.route('/delete_product/<int:product_id>')
def delete_product(product_id):
    supabase.table("inventory").delete().eq("id", product_id).execute()
    return redirect(url_for('products'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
