from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from collections import defaultdict
from datetime import datetime
from functools import wraps
import os
import time
import requests
from google import genai  # مكتبة Gemini

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fallback_dev_key")

# إعداد Supabase و Gemini
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- الدوال المساعدة ---
@app.context_processor
def inject_currency():
    company_code = session.get('company_code')
    if company_code:
        try:
            res = supabase.table("settings").select("currency").eq("company_code", company_code).execute()
            currency = res.data[0]['currency'] if res.data else ""
            return dict(currency=currency)
        except:
            return dict(currency="")
    return dict(currency="")

def send_telegram_alert_by_token(token, chat_id, message):
    if token and chat_id:
        try:
            requests.get(f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}")
        except Exception as e:
            print(f"Error: {e}")

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
        return "كود الشركة غير صحيح!", 401
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        company_code = request.form.get('company_code')
        company_name = request.form.get('company_name')
        res = supabase.table("settings").select("company_code").eq("company_code", company_code).execute()
        if res.data:
            return "هذا الكود مستخدم بالفعل، يرجى اختيار كود آخر!", 400
        try:
            supabase.table("settings").insert({"company_code": company_code, "company_name": company_name}).execute()
            return "تم إنشاء الحساب بنجاح! يمكنك الآن تسجيل الدخول."
        except Exception as e:
            return f"حدث خطأ أثناء الإنشاء: {e}", 500
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
    return render_template('settings.html', settings=res.data[0] if res.data else {})

# --- المسار المدمج للمنتجات (الرفع عبر Storage) ---
@app.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    company_code = session.get('company_code')
    
    if request.method == 'POST':
        try:
            # 1. التعامل مع الصورة
            file = request.files.get('product_image')
            image_link = ""
            
            if file and file.filename != '':
                file_name = f"{company_code}_{int(time.time())}_{file.filename}"
                supabase.storage.from_("product-images").upload(
                    path=file_name,
                    file=file.read(),
                    file_options={"content-type": file.content_type}
                )
                image_link = supabase.storage.from_("product-images").get_public_url(file_name)

            # 2. تجهيز البيانات
            data = {
                "name": request.form.get('name'),
                "quantity": int(request.form.get('quantity', 0)),
                "price": float(request.form.get('price', 0.0)),
                "company_id_text": company_code, 
                "product-images": image_link 
            }

            # 3. الإدراج
            supabase.table("inventory").insert(data).execute()
            return redirect(url_for('products'))

        except Exception as e:
            print(f"DEBUG ERROR: {e}")
            return f"حدث خطأ أثناء حفظ المنتج: {str(e)}", 500

    # الـ GET لجلب المنتجات
    products_res = supabase.table("inventory").select("*").eq("company_id_text", company_code).execute()
    return render_template('products.html', products=products_res.data or [])

@app.route('/orders', methods=['GET', 'POST'])
@login_required
def orders():
    company_code = session.get('company_code')
    res_settings = supabase.table("settings").select("currency, telegram_token, telegram_chat_id").eq("company_code", company_code).execute()
    currency = res_settings.data[0].get('currency', '') if res_settings.data else ""

    if request.method == 'POST':
        product_name = request.form.get('product_name')
        requested_qty = int(request.form.get('quantity', 0)) 
        data = {
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('customer_phone'), 
            "product_name": product_name,
            "quantity": requested_qty, 
            "total_price": float(request.form.get('price', 0.0)),
            "company_code": company_code,
            "status": "قيد الانتظار"
        }
        supabase.table("orders").insert(data).execute()
        
        if res_settings.data:
            settings_info = res_settings.data[0]
            token = settings_info.get('telegram_token')
            chat_id = settings_info.get('telegram_chat_id')
            msg = f"🛒 طلبية جديدة!\nالعميل: {request.form.get('customer_name')}\nالمنتج: {product_name}\nالكمية: {requested_qty}"
            send_telegram_alert_by_token(token, chat_id, msg)
            
            products_res = supabase.table("inventory").select("id, quantity, name").eq("name", product_name).eq("company_id_text", company_code).execute()
            if products_res.data:
                product = products_res.data[0] 
                new_qty = product['quantity'] - requested_qty
                supabase.table("inventory").update({"quantity": new_qty}).eq("id", product['id']).execute()
        return redirect(url_for('orders'))

    res = supabase.table("orders").select("*").eq("company_code", company_code).execute()
    return render_template('orders_dashboard.html', orders=res.data or [], currency=currency)

# --- (بقية المسارات: stats, webhook_instagram كما هي) ---

if __name__ == '__main__':
    refresh_instagram_token()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
