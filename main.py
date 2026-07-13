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
    if request.endpoint in ['login', 'static', 'home']: return
    if 'company_id' not in session: return redirect(url_for('login'))

# --- الدوال الأساسية (المنتجات والطلبيات والإعدادات) ---

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
                    supabase.storage.from_("product-images").upload(file_name, file.read(), {"content-type": f"image/{file_ext}"})
                    image_url = supabase.storage.from_("product-images").get_public_url(file_name)
                except: pass
        
        supabase.table("inventory").insert({
            "company_id": c_id, "name": request.form.get('name'),
            "quantity": int(request.form.get('quantity') or 0),
            "price": float(request.form.get('price') or 0),
            "image_url": image_url
        }).execute()
        return redirect(url_for('products'))
    
    res = supabase.table("inventory").select("*").eq("company_id", session['company_id']).execute()
    return render_template('products.html', products=res.data or [])

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        supabase.table("orders").insert({
            "company_id": session['company_id'],
            "customer_name": request.form.get('customer_name'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('price') or 0),
            "status": "قيد الانتظار"
        }).execute()
        return redirect(url_for('orders'))
    res = supabase.table("orders").select("*").eq("company_id", session['company_id']).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        supabase.table("companies").update({
            "store_name": request.form.get('store_name')
        }).eq("id", session['company_id']).execute()
        return redirect(url_for('settings'))
    res = supabase.table("companies").select("*").eq("id", session['company_id']).execute()
    return render_template('settings.html', settings=res.data[0] if res.data else {})

@app.route('/stats')
def stats():
    return render_template('stats.html')

# --- ربط Gemini ---
@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    products = supabase.table("inventory").select("name, price").eq("company_id", session['company_id']).execute()
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=f"أنت مساعد متجر. المنتجات: {products.data}. السؤال: {user_message}"
    )
    return {"reply": response.text}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        res = supabase.table("companies").select("*").eq("email", request.form.get('email')).execute()
        if res.data and res.data[0]['password'] == request.form.get('password'):
            session['company_id'] = res.data[0]['id']
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard(): return render_template('dashboard.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
