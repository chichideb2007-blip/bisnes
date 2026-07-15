from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key")

# إعداد Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# --- مسار الطلبيات ---
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'company_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        data = {
            "company_id": str(session['company_id']),
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('phone'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('price') or 0.0),
            "status": "new"
        }
        try:
            supabase.table("orders").insert(data).execute()
        except Exception as e:
            print(f"خطأ في حفظ الطلبية: {e}")
        return redirect(url_for('orders'))
    
    res = supabase.table("orders").select("*").eq("company_id", str(session['company_id'])).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

# --- مسار المنتجات (إضافة منتج جديد مع صورة) ---
@app.route('/products', methods=['GET', 'POST'])
def products():
    if 'company_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        image_url = None
        # معالجة الصورة إذا وجدت
        if 'product_image' in request.files:
            file = request.files['product_image']
            if file and file.filename != '':
                # ملاحظة: تأكدي من تغيير "your-bucket-name" إلى اسم الـ Bucket الفعلي في Supabase
                file_path = f"products/{session['company_id']}/{file.filename}"
                supabase.storage.from_("your-bucket-name").upload(path=file_path, file=file.read())
                image_url = supabase.storage.from_("your-bucket-name").get_public_url(file_path)

        # حفظ البيانات في جدول inventory
        data = {
            "company_id": str(session['company_id']),
            "name": request.form.get('name'),
            "quantity": int(request.form.get('quantity') or 0),
            "price": float(request.form.get('price') or 0.0),
            "image_url": image_url
        }
        try:
            supabase.table("inventory").insert(data).execute()
        except Exception as e:
            print(f"خطأ في حفظ المنتج: {e}")
            
        return redirect(url_for('products'))

    # جلب المنتجات للعرض
    res = supabase.table("inventory").select("*").eq("company_id", str(session['company_id'])).execute()
    return render_template('products.html', products=res.data or [])
