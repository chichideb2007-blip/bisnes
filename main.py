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

# --- (بقية الدوال المساعدة كما هي: inject_currency, send_telegram, refresh_instagram, login_required) ---
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

# --- المسار المحدث للمنتجات ---
@app.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    company_code = session.get('company_code')
    
    if request.method == 'POST':
        file = request.files.get('product_image')
        image_url = ""
        
        if file and file.filename != '':
            file_name = f"{company_code}_{int(time.time())}_{file.filename}"
            try:
                supabase.storage.from_("product-images").upload(
                    path=file_name,
                    file=file.read(),
                    file_options={"content-type": file.content_type}
                )
                image_url = supabase.storage.from_("product-images").get_public_url(file_name)
            except Exception as e:
                print(f"Error uploading image: {e}")

        data = {
            'name': request.form.get('name'),
            'quantity': int(request.form.get('quantity', 0)),
            'price': float(request.form.get('price', 0.0)),
            'company_code': company_code,
            'company_id': company_code,
            'image_url': image_url 
        }

        try:
            supabase.table('inventory').insert(data).execute()
            return redirect(url_for('products'))
        except Exception as e:
            return f"خطأ في الحفظ: {str(e)}", 500

    query = supabase.table('inventory').select('*').eq('company_code', company_code)
    search = request.args.get('search')
    if search: query = query.ilike('name', f'%{search}%')
    return render_template('products.html', products=query.execute().data or [])

# --- (بقية المسارات: orders, stats, webhook كما هي) ---

if __name__ == '__main__':
    refresh_instagram_token()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
