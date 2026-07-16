from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
import time

app = Flask(__name__)
app.secret_key = 'secret_key_123'

# إعداد Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# دالة لجلب معرف الشركة من الجلسة
def get_cid():
    return session.get('company_id')

@app.route('/')
def index():
    return redirect(url_for('login'))

# --- تسجيل حساب جديد ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        supabase.auth.sign_up({"email": email, "password": password})
        new_cid = f"comp_{int(time.time())}" 
        supabase.table("companies").insert({"email": email, "company_id": new_cid}).execute()
        return redirect(url_for('login'))
    return render_template('register.html')

# --- تسجيل الدخول ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            supabase.auth.sign_in_with_password({"email": email, "password": password})
            res = supabase.table("companies").select("company_id").eq("email", email).execute()
            if res.data:
                session['company_id'] = res.data[0]['company_id']
                return redirect(url_for('dashboard'))
        except:
            return "خطأ في تسجيل الدخول!"
    return render_template('login.html')

# --- لوحة التحكم ---
@app.route('/dashboard')
def dashboard():
    if not get_cid(): return redirect(url_for('login'))
    return render_template('dashboard.html')

# --- مسار المنتجات ---
@app.route('/products', methods=['GET', 'POST'])
def products():
    cid = get_cid()
    if not cid: return redirect(url_for('login'))

    if request.method == 'POST':
        image_url = None
        if 'product_image' in request.files:
            file = request.files['product_image']
            if file and file.filename != '':
                unique_filename = f"{int(time.time())}_{file.filename}"
                file_path = f"products/{unique_filename}"
                try:
                    supabase.storage.from_("product-images").upload(path=file_path, file=file.read())
                    image_url = supabase.storage.from_("product-images").get_public_url(file_path)
                except Exception as e:
                    print(f"Error: {e}")
        
        data = {
            "name": request.form.get('name'),
            "quantity": int(request.form.get('quantity', 0)),
            "price": float(request.form.get('price', 0.0)),
            "image_url": image_url,
            "company_id_text": cid
        }
        supabase.table("inventory").insert(data).execute()
        return redirect(url_for('products'))

    res = supabase.table("inventory").select("*").eq("company_id_text", cid).execute()
    return render_template('products.html', products=res.data or [])

# --- مسار الطلبات ---
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    cid = get_cid()
    if not cid: return redirect(url_for('login'))

    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('phone'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('price', 0.0)),
            "company_id_text": cid
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    res = supabase.table("orders").select("*").eq("company_id_text", cid).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

# --- مسار الإحصائيات (بسيط ومباشر) ---
@app.route('/stats')
def stats():
    if not get_cid(): return redirect(url_for('login'))
    return render_template('stats.html')

# --- مسارات إضافية ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect(url_for('orders'))

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    supabase.table("inventory").delete().eq("id", product_id).execute()
    return redirect(url_for('products'))

if __name__ == '__main__':
    app.run(debug=True)
