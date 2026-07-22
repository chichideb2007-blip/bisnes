from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from functools import wraps
import os
import requests
import base64
from google import genai
from google.genai import types

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fallback_dev_key")

# إعداد Supabase و Gemini
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- الدوال المساعدة ---

def get_company_by_slug(slug):
    res = supabase.table("settings").select("*").eq("company_slug", slug).execute()
    return res.data[0] if res.data else None

def send_telegram_alert_by_token(token, chat_id, message):
    if not token or not chat_id: return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        response = requests.get(url, params={"chat_id": chat_id, "text": message})
        return response.status_code == 200
    except: return False

def send_instagram_message(page_access_token, recipient_id, message_text):
    url = f"https://graph.facebook.com/v20.0/me/messages"
    params = {"access_token": page_access_token}
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    response = requests.post(url, params=params, json=data)
    return response.json()

def refresh_instagram_token():
    res = supabase.table("settings").select("company_slug, instagram_token").execute()
    for row in res.data:
        old_token = row.get('instagram_token')
        if old_token:
            url = f"https://graph.facebook.com/v20.0/oauth/access_token?grant_type=fb_exchange_token&client_id={os.environ.get('APP_ID')}&client_secret={os.environ.get('APP_SECRET')}&fb_exchange_token={old_token}"
            try:
                response = requests.get(url).json()
                new_token = response.get('access_token')
                if new_token:
                    supabase.table("settings").update({"instagram_token": new_token}).eq("company_slug", row['company_slug']).execute()
            except: pass

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'company_slug' not in session: return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- المسارات ---

@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        slug = request.form.get('company_slug', '').lower()
        if get_company_by_slug(slug):
            session['company_slug'] = slug
            return redirect(url_for('dashboard'))
        return "اسم المتجر غير موجود!", 401
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        slug = request.form.get('company_slug').lower()
        name = request.form.get('company_name')
        if get_company_by_slug(slug): return "هذا الاسم مستخدم!", 400
        supabase.table("settings").insert({"company_slug": slug, "company_name": name}).execute()
        return "تم إنشاء الحساب!"
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('company_slug', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard(): return render_template('dashboard.html')

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    slug = session.get('company_slug')
    if request.method == 'POST':
        data = {
            "company_name": request.form.get('shop_name'),
            "telegram_token": request.form.get('bot_token'),
            "telegram_chat_id": request.form.get('chat_id'),
            "currency": request.form.get('currency'),
            "delivery_home_price": float(request.form.get('delivery_home_price', 0)),
            "delivery_office_price": float(request.form.get('delivery_office_price', 0))
        }
        supabase.table("settings").update(data).eq("company_slug", slug).execute()
        return redirect(url_for('settings'))
    return render_template('settings.html', settings=get_company_by_slug(slug))

@app.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    slug = session.get('company_slug')
    if request.method == 'POST':
        file = request.files.get('product_image')
        encoded = f'data:image/jpeg;base64,{base64.b64encode(file.read()).decode("utf-8")}' if file else ""
        data = {'name': request.form.get('name'), 'quantity': int(request.form.get('quantity', 0)), 'price': float(request.form.get('price', 0)), 'company_slug': slug, 'product-images': encoded}
        supabase.table('inventory').insert(data).execute()
        return redirect(url_for('products'))
    return render_template('products.html', products=supabase.table("inventory").select("*").eq("company_slug", slug).execute().data or [])

@app.route('/orders', methods=['GET', 'POST'])
@login_required
def orders():
    slug = session.get('company_slug')
    company = get_company_by_slug(slug)
    if request.method == 'POST':
        data = {"customer_name": request.form.get('customer_name'), "product_name": request.form.get('product_name'), "company_slug": slug, "status": "قيد الانتظار"}
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    return render_template('orders_dashboard.html', orders=supabase.table("orders").select("*").eq("company_slug", slug).execute().data or [], currency=company.get('currency', ''))

@app.route('/webhook_instagram', methods=['GET', 'POST'])
def webhook_instagram():
    if request.method == 'GET':
        if request.args.get('hub.verify_token') == "MY_VERIFY_TOKEN_SECRET":
            return request.args.get('hub.challenge')
        return 'Invalid token', 403

    data = request.json
    try:
        page_id = data['entry'][0]['id']
        messaging = data['entry'][0]['messaging'][0]
        sender_id = messaging['sender']['id']
        msg = messaging['message']['text']

        res = supabase.table("settings").select("*").eq("instagram_page_id", page_id).execute()
        if res.data:
            s = res.data[0]
            send_telegram_alert_by_token(s['telegram_token'], s['telegram_chat_id'], f"🔔 رسالة من ({sender_id}):\n{msg}")
            
            response = client.models.generate_content(model='gemini-2.0-flash', contents=msg)
            ai_reply = response.text
            
            send_instagram_message(s['page_access_token'], sender_id, ai_reply)
            
            send_telegram_alert_by_token(s['telegram_token'], s['telegram_chat_id'], f"🤖 الرد التلقائي: {ai_reply}")

        return 'OK', 200
    except Exception as e:
        print(f"Error: {e}")
        return 'Error', 500

@app.route('/shop/<company_slug>')
def shop_page(company_slug):
    company = get_company_by_slug(company_slug)
    if not company: return "المتجر غير موجود", 404
    products = supabase.table("inventory").select("*").eq("company_slug", company_slug).execute().data or []
    return render_template('public_shop.html', products=products, company=company)

@app.route('/order/<int:product_id>', methods=['GET', 'POST'])
def finalize_order(product_id):
    product = supabase.table("inventory").select("*").eq("id", product_id).execute().data[0]
    company = get_company_by_slug(product['company_slug'])
    
    if request.method == 'POST':
        if product['quantity'] <= 0: return "نفذت الكمية!"
        
        shipping = float(request.form.get('shipping_cost', 0))
        total = float(product['price']) + shipping
        
        order_data = {
            "customer_name": request.form.get('customer_name'),
            "product_name": product['name'],
            "total_price": total,
            "company_slug": product['company_slug'],
            "status": "قيد الانتظار"
        }
        supabase.table("orders").insert(order_data).execute()
        supabase.table("inventory").update({"quantity": product['quantity'] - 1}).eq("id", product_id).execute()
        
        msg = f"طلب جديد: {product['name']} | المجموع: {total}"
        send_telegram_alert_by_token(company.get('telegram_token'), company.get('telegram_chat_id'), msg)
        
        return "تم الطلب بنجاح!"
    
    return render_template('checkout.html', product=product, settings=company)

if __name__ == '__main__':
    refresh_instagram_token()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
