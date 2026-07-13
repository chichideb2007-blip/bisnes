from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from google import genai
import os, uuid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

# إعداد الاتصال
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.before_request
def check_session():
    if request.endpoint in ['login', 'register', 'static', 'home']: return
    if 'company_id' not in session: return redirect(url_for('login'))

# --- Routes ---

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        # حفظ طلبية جديدة
        data = {
            "company_id": session['company_id'],
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('phone'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('price') or 0),
            "status": "قيد الانتظار"
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    # عرض الطلبيات
    res = supabase.table("orders").select("*").eq("company_id", session['company_id']).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

@app.route('/products', methods=['GET', 'POST'])
def products():
    if request.method == 'POST':
        c_id = session.get('company_id')
        image_url = None
        
        # معالجة الصورة
        if 'product_image' in request.files:
            file = request.files['product_image']
            if file and file.filename != '':
                file_ext = file.filename.split('.')[-1]
                file_name = f"{uuid.uuid4()}.{file_ext}"
                try:
                    # رفع للصورة باستخدام bucket باسم product-images
                    supabase.storage.from_("product-images").upload(
                        path=file_name,
                        file=file.read(),
                        file_options={"content-type": f"image/{file_ext}", "upsert": "true"}
                    )
                    image_url = supabase.storage.from_("product-images").get_public_url(file_name)
                except Exception as e:
                    print(f"Error uploading image: {e}")

        # إضافة المنتج لقاعدة البيانات
        new_product = {
            "company_id": c_id,
            "name": request.form.get('name'),
            "quantity": int(request.form.get('quantity') or 0),
            "price": float(request.form.get('price') or 0),
            "image_url": image_url
        }
        supabase.table("inventory").insert(new_product).execute()
        return redirect(url_for('products'))
    
    # عرض المنتجات
    res = supabase.table("inventory").select("*").eq("company_id", session['company_id']).execute()
    return render_template('products.html', products=res.data or [])

# بقية الدوال (login, logout, settings, etc.) تبقى كما هي...
