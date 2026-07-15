from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
import time

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

# --- مسار المنتجات (المخزون) - النسخة المصححة ---
@app.route('/products', methods=['GET', 'POST'])
def products():
    if request.method == 'POST':
        image_url = None
        # معالجة الصورة
        if 'product_image' in request.files:
            file = request.files['product_image']
            if file and file.filename != '':
                # استخدام وقت النظام لضمان اسم فريد وتجنب أخطاء التكرار
                unique_filename = f"{int(time.time())}_{file.filename}"
                file_path = f"products/{unique_filename}"
                
                try:
                    supabase.storage.from_("product-images").upload(path=file_path, file=file.read())
                    image_url = supabase.storage.from_("product-images").get_public_url(file_path)
                except Exception as e:
                    print(f"Error uploading image: {e}")
        
        # حفظ البيانات مع التأكد من تحويل الأنواع (مهم جداً)
        try:
            data = {
                "name": request.form.get('name'),
                "quantity": int(request.form.get('quantity', 0)), # تحويل لعدد صحيح
                "price": float(request.form.get('price', 0.0)),   # تحويل لرقم عشري
                "image_url": image_url,
                "company_id": "1"  # الالتزام باسم العمود الموحد
            }
            supabase.table("inventory").insert(data).execute()
        except Exception as e:
            print(f"Database Error: {e}")
            return "حدث خطأ أثناء حفظ البيانات في قاعدة البيانات، تأكدي من نوع البيانات."

        return redirect(url_for('products'))

    # عرض المنتجات
    res = supabase.table("inventory").select("*").execute()
    return render_template('products.html', products=res.data or [])

# --- مسار الطلبات ---
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        # استخدام أسماء الأعمدة الدقيقة لجدول orders
        data = {
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('phone'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('price', 0.0)),
            "company_id": "1"
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    res = supabase.table("orders").select("*").execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

# --- مسارات إضافية (الخروج والحذف) ---
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
