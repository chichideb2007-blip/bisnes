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
    return redirect(url_for('login'))

# --- مسار تسجيل الدخول ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['company_id'] = "1"
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# --- مسار لوحة التحكم ---
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# --- مسار المنتجات (المخزون) ---
@app.route('/products', methods=['GET', 'POST'])
def products():
    if request.method == 'POST':
        image_url = None
        # معالجة رفع الصورة
        if 'product_image' in request.files:
            file = request.files['product_image']
            if file and file.filename != '':
                file_path = f"products/{file.filename}"
                supabase.storage.from_("products_images").upload(path=file_path, file=file.read())
                image_url = supabase.storage.from_("products_images").get_public_url(file_path)

        # حفظ البيانات في Supabase (تم تحديث الاسم لـ company_id_text)
        data = {
            "name": request.form.get('name'),
            "quantity": request.form.get('quantity'),
            "price": request.form.get('price'),
            "image_url": image_url,
            "company_id_text": "1"  
        }
        supabase.table("inventory").insert(data).execute()
        return redirect(url_for('products'))

    # عرض المنتجات
    res = supabase.table("inventory").select("*").execute()
    return render_template('products.html', products=res.data or [])

# --- مسار الطلبات ---
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        data = {"customer_name": request.form.get('request_name'), "company_id": "1"}
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    res = supabase.table("orders").select("*").execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

if __name__ == '__main__':
    app.run(debug=True)
