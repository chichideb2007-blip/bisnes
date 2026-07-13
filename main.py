from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from google import genai
import os, uuid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

# إعداد الاتصال
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# 1. تعريف دالة التحقق من الجلسة (قبل المسارات)
@app.before_request
def check_session():
    # قائمة المسارات المسموح بها بدون تسجيل دخول
    allowed_routes = ['login', 'static', 'home']
    if request.endpoint in allowed_routes:
        return
    
    # إذا لم يكن المستخدم مسجلاً، وجهه إلى صفحة تسجيل الدخول
    if 'company_id' not in session:
        return redirect(url_for('login'))

# --- المسارات (Routes) ---

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
            
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
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
    
    res = supabase.table("orders").select("*").eq("company_id", session['company_id']).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

@app.route('/products', methods=['GET', 'POST'])
def products():
    if request.method == 'POST':
        c_id = session.get('company_id')
        image_url = None
        
        if 'product_image' in request.files:
            file = request.files['product_image']
            if file and file.filename != '':
                file_ext = file.filename.split('.')[-1]
                file_name = f"{uuid.uuid4()}.{file_ext}"
                try:
                    supabase.storage.from_("product-images").upload(
                        path=file_name,
                        file=file.read(),
                        file_options={"content-type": f"image/{file_ext}", "upsert": "true"}
                    )
                    image_url = supabase.storage.from_("product-images").get_public_url(file_name)
                except Exception as e:
                    print(f"Error uploading image: {e}")

        new_product = {
            "company_id": c_id,
            "name": request.form.get('name'),
            "quantity": int(request.form.get('quantity') or 0),
            "price": float(request.form.get('price') or 0),
            "image_url": image_url
        }
        supabase.table("inventory").insert(new_product).execute()
        return redirect(url_for('products'))
    
    res = supabase.table("inventory").select("*").eq("company_id", session['company_id']).execute()
    return render_template('products.html', products=res.data or [])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
