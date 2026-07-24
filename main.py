from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from supabase import create_client
from collections import defaultdict
from datetime import datetime
from functools import wraps
import os
import time
import requests
import urllib.parse
import base64
from google import genai 
from google.genai import types 

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fallback_dev_key")

# إعداد Supabase و Gemini
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- المعالج التلقائي للعملة ---
@app.context_processor
def inject_currency():
    company_code = session.get('company_code')
    if company_code:
        try:
            res = supabase.table('settings').select("currency").eq("company_code", company_code).single().execute()
            if res.data:
                return dict(currency=res.data.get('currency', ''))
        except:
            pass
    return dict(currency='DA')

# --- الدوال المساعدة ---

def send_telegram_alert_by_token(token, chat_id, message):
    if not token or not chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        params = {"chat_id": chat_id, "text": message}
        response = requests.get(url, params=params)
        return response.status_code == 200
    except Exception as e:
        return False

def refresh_instagram_token():
    res = supabase.table("settings").select("company_code, instagram_token").execute()
    for row in res.data:
        old_token = row.get('instagram_token')
        if old_token:
            url = f"https://graph.facebook.com/v20.0/oauth/access_token?grant_type=fb_exchange_token&client_id={os.environ.get('APP_ID')}&client_secret={os.environ.get('APP_SECRET')}&fb_exchange_token={old_token}"
            try:
                response = requests.get(url).json()
                new_token = response.get('access_token')
                if new_token:
                    supabase.table("settings").update({"instagram_token": new_token}).eq("company_code", row['company_code']).execute()
            except Exception as e:
                print(f"Token Refresh Error: {e}")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'company_code' not in session: return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- المسارات ---

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        company_code = request.form.get('company_code')
        res = supabase.table("settings").select("company_code").eq("company_code", company_code).execute()
        if res.data:
            session['company_code'] = company_code
            return redirect(url_for('dashboard'))
        else:
            return "كود الشركة غير صحيح، يرجى التأكد منه أو إنشاء حساب جديد.", 401
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        company_code = request.form.get('company_code')
        company_name = request.form.get('company_name')
        res = supabase.table("settings").select("company_code").eq("company_code", company_code).execute()
        if res.data: return "هذا الكود مستخدم بالفعل، يرجى اختيار كود آخر!", 400
        try:
            supabase.table("settings").insert({"company_code": company_code, "company_name": company_name}).execute()
            return "تم إنشاء الحساب بنجاح!"
        except Exception as e:
            return f"حدث خطأ: {e}", 500
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('company_code', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    company_code = session.get('company_code')
    currencies = [("USD", "دولار أمريكي"), ("EUR", "يورو"), ("DZD", "دينار جزائري"), ("SAR", "ريال سعودي")] # تم اختصارها للسرعة
    if request.method == 'POST':
        data = {
            "company_name": request.form.get('shop_name'),
            "telegram_token": request.form.get('bot_token'),
            "telegram_chat_id": request.form.get('chat_id'),
            "instagram_url": request.form.get('instagram_link'),
            "currency": request.form.get('currency') 
        }
        supabase.table("settings").update(data).eq("company_code", company_code).execute()
        return redirect(url_for('settings'))
    res = supabase.table("settings").select("*").eq("company_code", company_code).execute()
    settings_data = res.data[0] if res.data else {}
    return render_template('settings.html', settings=settings_data, currencies=currencies)

@app.route('/shipping_settings', methods=['GET', 'POST'])
@login_required
def shipping_settings():
    if request.method == 'POST':
        wilaya_id = request.form.get('id')
        supabase.table("shipping_rates").update({
            "office_price": float(request.form.get('office_price')),
            "home_price": float(request.form.get('home_price'))
        }).eq("id", wilaya_id).execute()
        return redirect(url_for('shipping_settings'))
    res = supabase.table("shipping_rates").select("*").order("id").execute()
    return render_template('shipping_settings.html', rates=res.data)

# --- مسارات API لأسعار التوصيل الجديدة ---

@app.route('/get_delivery_prices', methods=['GET'])
@login_required
def get_delivery_prices():
    company_code = session.get('company_code')
    data = supabase.table("delivery_prices").select("*").eq("company_code", company_code).execute()
    return jsonify(data.data)

@app.route('/update_delivery_price', methods=['POST'])
@login_required
def update_delivery_price():
    data = request.json
    row_id = data['id']
    new_office = data['office_price']
    new_home = data['home_price']
    supabase.table("delivery_prices").update({
        "office_price": new_office,
        "home_price": new_home
    }).eq("id", row_id).execute()
    return jsonify({"status": "success"})

# --- مسارات المنتجات والطلبات ---

@app.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    company_code = session.get('company_code')
    if request.method == 'POST':
        file = request.files.get('product_image')
        encoded_string = ""
        if file and file.filename != '':
            encoded_string = f'data:image/jpeg;base64,{base64.b64encode(file.read()).decode("utf-8")}'
        data = {
            'name': request.form.get('name'),
            'quantity': int(request.form.get('quantity', 0)),
            'price': float(request.form.get('price', 0.0)),
            'company_id_text': company_code,
            'product-images': encoded_string
        }
        supabase.table('inventory').insert(data).execute()
        return redirect(url_for('products'))
    res = supabase.table("inventory").select("*").eq("company_id_text", company_code).execute()
    return render_template('products.html', products=res.data or [])

@app.route('/inventory_management', methods=['GET', 'POST'])
@login_required
def inventory_management():
    company_code = session.get('company_code')
    if request.method == 'POST':
        product_id = request.form.get('product_id')
        new_quantity = request.form.get('quantity')
        file = request.files.get('product_image')
        update_data = {"quantity": int(new_quantity)}
        if file and file.filename != '':
            filename = f"{company_code}/{int(time.time())}_{file.filename}"
            supabase.storage.from_("products").upload(path=filename, file=file.read(), file_options={"content-type": file.content_type})
            public_url = supabase.storage.from_("products").get_public_url(filename)
            update_data["product-images"] = public_url
        supabase.table('inventory').update(update_data).eq("id", product_id).eq("company_id_text", company_code).execute()
    res = supabase.table("inventory").select("*").eq("company_id_text", company_code).execute()
    return render_template('inventory_management.html', inventory=res.data or [])

@app.route('/delete_product/<int:id>', methods=['POST'])
@login_required
def delete_product(id):
    supabase.table("inventory").delete().eq("id", id).execute()
    return redirect(url_for('products'))

@app.route('/orders', methods=['GET', 'POST'])
@login_required
def orders():
    company_code = session.get('company_code')
    if request.method == 'POST':
        product_name = request.form.get('product_name')
        requested_qty = int(request.form.get('quantity', 0))
        customer_name = request.form.get('customer_name')
        state = request.form.get('state')
        delivery_type = request.form.get('delivery_type')
        delivery_price = float(request.form.get('delivery_price', 0.0))
        base_price = float(request.form.get('price', 0.0))
        total_price = base_price + delivery_price
        
        data = {
            "customer_name": customer_name,
            "product_name": product_name,
            "quantity": requested_qty, 
            "total_price": total_price,
            "company_code": company_code,
            "status": "قيد الانتظار",
            "state": state,
            "delivery_type": delivery_type,
            "delivery_price": delivery_price
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    res = supabase.table("orders").select("*").eq("company_code", company_code).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

@app.route('/submit-order', methods=['POST'])
def submit_order():
    data = request.form
    customer_name = data.get('customer_name')
    customer_last_name = data.get('customer_last_name')
    phone = data.get('phone')
    product_id = data.get('product_id')
    wilaya_id = data.get('wilaya') 
    delivery_type = data.get('delivery_type') 
    
    product_res = supabase.table("inventory").select("price, name, company_id_text").eq("id", product_id).single().execute()
    product = product_res.data
    shipping_res = supabase.table("delivery_prices").select("home_price, office_price").eq("id", int(wilaya_id)).single().execute()
    shipping_data = shipping_res.data
    
    delivery_price = float(shipping_data['home_price']) if delivery_type == 'home' else float(shipping_data['office_price'])
    base_price = float(product['price'])
    total_price = base_price + delivery_price
    
    order_data = {
        "customer_name": f"{customer_name} {customer_last_name}",
        "customer_phone": phone,
        "product_name": product['name'],
        "total_price": total_price,
        "delivery_price": delivery_price,
        "status": "قيد الانتظار",
        "company_code": product['company_id_text']
    }
    supabase.table("orders").insert(order_data).execute()
    supabase.rpc('decrement_stock', {'p_id': int(product_id), 'qty': 1}).execute()
    return "تم استلام طلبك بنجاح!"

@app.route('/stats')
@login_required
def stats():
    company_code = session.get('company_code')
    res_orders = supabase.table("orders").select("total_price, created_at").eq("company_code", company_code).execute()
    return render_template('stats.html', total_orders=len(res_orders.data))

# المسارات المتبقية (webhook_instagram و shop...) يتم وضعها هنا بنفس الترتيب
@app.route('/webhook_instagram', methods=['GET', 'POST'])
def webhook_instagram():
    if request.method == 'GET': return request.args.get('hub.challenge')
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)
