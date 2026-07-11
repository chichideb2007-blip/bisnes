from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from google import genai
import os, uuid, requests

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.before_request
def check_session():
    if request.endpoint in ['login', 'register', 'static', 'home']: return
    if 'company_id' not in session: return redirect(url_for('login'))

def get_gemini_response(company_id, user_message):
    products = supabase.table("inventory").select("name, price, quantity").eq("company_id", company_id).execute()
    prod_list = str(products.data)
    system_instruction = f"أنت مساعد مبيعات ذكي لمتجر جزائري. قائمة منتجاتنا: {prod_list}. أجب الزبون بنفس اللغة."
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=system_instruction + "\nرسالة الزبون: " + user_message
    )
    return response.text

@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard(): return render_template('dashboard.html')

@app.route('/statistics')
def stats(): return render_template('stats.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        supabase.table("orders").insert({
            "company_id": session['company_id'],
            "company_id_text": str(session['company_id']),
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('phone'), 
            "product_name": request.form.get('product_name'),
            "price": request.form.get('price')
        }).execute()
        return redirect(url_for('orders'))
    
    res = supabase.table("orders").select("*").eq("company_id", session['company_id']).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

@app.route('/delete_order/<int:order_id>')
def delete_order(order_id):
    supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect(url_for('orders'))

@app.route('/products', methods=['GET', 'POST'])
def products():
    if request.method == 'POST':
        c_id = session.get('company_id')
        
        # 1. معالجة رفع الصورة
        image_url = None
        if 'product_image' in request.files:
            file = request.files['product_image']
            if file and file.filename != '':
                # إنشاء اسم فريد للملف
                file_ext = file.filename.split('.')[-1]
                file_name = f"{uuid.uuid4()}.{file_ext}"
                
                # رفع الملف إلى Supabase Storage (Bucket باسم 'products')
                supabase.storage.from_("products").upload(
                    path=file_name,
                    file=file.read(),
                    file_options={"content-type": f"image/{file_ext}"}
                )
                
                # الحصول على الرابط العام
                image_url = supabase.storage.from_("products").get_public_url(file_name)

        # 2. حفظ البيانات في الجدول
        new_product = {
            "company_id": c_id,
            "company_id_text": str(c_id),
            "name": request.form.get('name'),
            "quantity": int(request.form.get('quantity') or 0),
            "price": float(request.form.get('price') or 0),
            "image_url": image_url # إضافة رابط الصورة
        }
        supabase.table("inventory").insert(new_product).execute()
        return redirect(url_for('products'))
    
    res = supabase.table("inventory").select("*").eq("company_id", session['company_id']).execute()
    return render_template('products.html', products=res.data or [])

@app.route('/delete_product/<int:product_id>')
def delete_product(product_id):
    supabase.table("inventory").delete().eq("id", product_id).execute()
    return redirect(url_for('products'))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        supabase.table("companies").update({
            "store_name": request.form.get('store_name'),
            "telegram_token": request.form.get('telegram_token')
        }).eq("id", session['company_id']).execute()
        return redirect(url_for('settings'))
    
    res = supabase.table("companies").select("*").eq("id", session['company_id']).execute()
    settings_data = res.data[0] if res.data else {}
    return render_template('settings.html', settings=settings_data)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        res = supabase.table("companies").select("*").eq("email", request.form.get('email')).execute()
        if res.data and res.data[0]['password'] == request.form.get('password'):
            session['company_id'] = res.data[0]['id']
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
