from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from collections import defaultdict
from datetime import datetime
from functools import wraps
import os
import time
import requests
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
    company_slug = session.get('company_slug')
    if company_slug:
        try:
            res = supabase.table("settings").select("currency").eq("company_slug", company_slug).execute()
            currency = res.data[0]['currency'] if res.data else ""
            return dict(currency=currency)
        except:
            return dict(currency="")
    return dict(currency="")

# --- الدوال المساعدة ---

def get_company_by_slug(slug):
    res = supabase.table("settings").select("*").eq("company_slug", slug).execute()
    return res.data[0] if res.data else None

def send_telegram_alert_by_token(token, chat_id, message):
    if not token or not chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        params = {"chat_id": chat_id, "text": message}
        response = requests.get(url, params=params)
        return response.status_code == 200
    except Exception as e:
        print(f"DEBUG: خطأ في الاتصال بتليجرام: {e}")
        return False

def refresh_instagram_token():
    # تحديث توكن إنستغرام لجميع المتاجر المسجلة
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
            except Exception as e:
                print(f"Token Refresh Error: {e}")

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
        slug = request.form.get('company_slug').lower()
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
        if get_company_by_slug(slug): return "هذا المتجر موجود بالفعل!", 400
        supabase.table("settings").insert({"company_slug": slug, "company_name": name}).execute()
        return "تم إنشاء الحساب بنجاح!"
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
        encoded_string = f'data:image/jpeg;base64,{base64.b64encode(file.read()).decode("utf-8")}' if file else ""
        data = {'name': request.form.get('name'), 'quantity': int(request.form.get('quantity', 0)), 'price': float(request.form.get('price', 0.0)), 'company_slug': slug, 'product-images': encoded_string}
        supabase.table('inventory').insert(data).execute()
        return redirect(url_for('products'))
    return render_template('products.html', products=supabase.table("inventory").select("*").eq("company_slug", slug).execute().data or [])

@app.route('/orders', methods=['GET', 'POST'])
@login_required
def orders():
    slug = session.get('company_slug')
    settings_info = get_company_by_slug(slug)
    
    if request.method == 'POST':
        product_name = request.form.get('product_name')
        requested_qty = int(request.form.get('quantity', 0))
        data = {
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('customer_phone'), 
            "product_name": product_name,
            "quantity": requested_qty, 
            "total_price": float(request.form.get('price', 0.0)),
            "company_slug": slug,
            "status": "قيد الانتظار"
        }
        supabase.table("orders").insert(data).execute()
        
        token = settings_info.get('telegram_token')
        chat_id = settings_info.get('telegram_chat_id')
        if token and chat_id:
            msg = f"🛒 طلبية جديدة!\nالعميل: {request.form.get('customer_name')}\nالمنتج: {product_name}"
            send_telegram_alert_by_token(token, chat_id, msg)
            inv = supabase.table("inventory").select("id, quantity").eq("name", product_name).eq("company_slug", slug).execute().data
            if inv:
                new_qty = max(0, inv[0]['quantity'] - requested_qty)
                supabase.table("inventory").update({"quantity": new_qty}).eq("id", inv[0]['id']).execute()
        return redirect(url_for('orders'))

    return render_template('orders_dashboard.html', orders=supabase.table("orders").select("*").eq("company_slug", slug).execute().data or [], currency=settings_info.get('currency', ''))

@app.route('/webhook_instagram', methods=['GET', 'POST'])
def webhook_instagram():
    if request.method == 'GET': return request.args.get('hub.challenge')
    data = request.json
    try:
        page_id = data['entry'][0]['id']
        messaging = data['entry'][0]['messaging'][0]
        msg = messaging['message']['text']
        sender_id = messaging['sender']['id']
        
        # البحث عن المتجر عبر معرف الصفحة
        res = supabase.table("settings").select("*").eq("instagram_page_id", page_id).execute()
        if res.data:
            s = res.data[0]
            send_telegram_alert_by_token(s['telegram_token'], s['telegram_chat_id'], f"🔔 رسالة من ({sender_id}):\n{msg}")
            
            my_system_instruction = "أنت مساعد مبيعات ذكي..."
            response = client.models.generate_content(model='gemini-2.0-flash', contents=msg, config=types.GenerateContentConfig(system_instruction=my_system_instruction))
            ai_reply = response.text
            
            send_telegram_alert_by_token(s['telegram_token'], s['telegram_chat_id'], f"🤖 الرد: {ai_reply}")
        return 'OK', 200
    except Exception as e:
        return 'Error', 500

@app.route('/shop/<company_slug>')
def shop_page(company_slug):
    company = get_company_by_slug(company_slug)
    if not company: return "المتجر غير موجود", 404
    products = supabase.table("inventory").select("*").eq("company_slug", company_slug).execute().data or []
    return render_template('public_shop.html', products=products, company=company)

@app.route('/order/<int:product_id>', methods=['GET', 'POST'])
def finalize_order(product_id):
    # 1. جلب المنتج
    product_res = supabase.table("inventory").select("*").eq("id", product_id).execute()
    if not product_res.data: return "المنتج غير موجود", 404
    product = product_res.data[0]
    
    # 2. جلب إعدادات الشركة
    company = get_company_by_slug(product['company_slug'])
    
    if request.method == 'POST':
        # التحقق من الكمية
        if product['quantity'] <= 0: return "عذراً، المنتج قد نفذ."
        
        # حساب السعر
        shipping = float(request.form.get('shipping_cost', 0))
        total_price = float(product['price']) + shipping
        
        # حفظ الطلب
        order_data = {
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('customer_phone'),
            "shipping_address": request.form.get('state'),
            "product_name": product['name'],
            "total_price": total_price,
            "company_slug": product['company_slug'],
            "status": "قيد الانتظار"
        }
        supabase.table("orders").insert(order_data).execute()
        
        # تنقيص المخزون
        supabase.table("inventory").update({"quantity": product['quantity'] - 1}).eq("id", product_id).execute()
        
        # إرسال التنبيه
        token = company.get('telegram_token')
        chat_id = company.get('telegram_chat_id')
        if token and chat_id:
            msg = f"📦 طلبية جديدة عبر الموقع!\nالمنتج: {product['name']}\nالزبون: {request.form.get('customer_name')}\nالمجموع: {total_price}"
            send_telegram_alert_by_token(token, chat_id, msg)
            
        return "تم الطلب بنجاح!"
    
    return render_template('checkout.html', product=product, settings=company)

if __name__ == '__main__':
    refresh_instagram_token()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
