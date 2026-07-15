from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__, template_folder='templates')
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

# إعداد Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# 1. الدخول والتوجه للموقع
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        res = supabase.table("companies").select("*").eq("email", email).execute()
        if res.data and res.data[0]['password'] == password:
            session['company_id'] = res.data[0]['id']
            return redirect(url_for('dashboard'))
        return "بيانات الدخول خاطئة"
    return render_template('login.html')

# 2. لوحة التحكم
@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

# 3. الطلبيات (المسار الصحيح)
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'company_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        data = {
            "company_id": session['company_id'],
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('phone'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('price') or 0.0)
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    res = supabase.table("orders").select("*").eq("company_id", session['company_id']).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

# 4. المنتجات
@app.route('/products', methods=['GET', 'POST'])
def products():
    if 'company_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        file = request.files.get('product_image')
        image_url = ""
        if file:
            try:
                supabase.storage.from_("inventory-images").upload(file.filename, file.read())
                image_url = f"https://{os.environ.get('PROJECT_ID')}.supabase.co/storage/v1/object/public/inventory-images/{file.filename}"
            except Exception as e:
                print(f"Error: {e}")
        
        data = {
            "company_id": session['company_id'],
            "name": request.form.get('name'),
            "quantity": int(request.form.get('quantity') or 0),
            "price": float(request.form.get('price') or 0.0),
            "image_url": image_url
        }
        supabase.table("inventory").insert(data).execute()
        return redirect(url_for('products'))
    
    res = supabase.table("inventory").select("*").eq("company_id", session['company_id']).execute()
    return render_template('products.html', products=res.data or [])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run()
