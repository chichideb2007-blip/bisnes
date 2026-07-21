from flask import Flask, render_template, request, redirect, url_for, session
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
            res = supabase.table("settings").select("currency").eq("company_code", company_code).execute()
            currency = res.data[0]['currency'] if res.data else ""
            return dict(currency=currency)
        except:
            return dict(currency="")
    return dict(currency="")

# --- الدوال المساعدة ---

def send_telegram_alert_by_token(token, chat_id, message):
    if not token or not chat_id: return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        return requests.get(url, params={"chat_id": chat_id, "text": message}).status_code == 200
    except: return False

def refresh_token_for_company(company_code, old_token):
    url = f"https://graph.facebook.com/v20.0/oauth/access_token?grant_type=fb_exchange_token&client_id={os.environ.get('APP_ID')}&client_secret={os.environ.get('APP_SECRET')}&fb_exchange_token={old_token}"
    try:
        new_token = requests.get(url).json().get('access_token')
        if new_token:
            supabase.table("settings").update({"instagram_token": new_token}).eq("company_code", company_code).execute()
            return new_token
    except: pass
    return old_token

def send_instagram_reply(page_token, recipient_id, message_text):
    url = f"https://graph.facebook.com/v20.0/me/messages"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": message_text}}
    return requests.post(url, params={"access_token": page_token}, json=payload)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'company_code' not in session: return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- المسارات ---

@app.route('/')
def home(): return redirect(url_for('login'))

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
        if res.data: return "هذا الكود مستخدم بالفعل!", 400
        supabase.table("settings").insert({"company_code": company_code, "company_name": company_name}).execute()
        return "تم إنشاء الحساب بنجاح!"
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('company_code', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard(): return render_template('dashboard.html')

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

@app.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    company_code = session.get('company_code')
    if request.method == 'POST':
        file = request.files.get('product_image')
        encoded_string = f'data:image/jpeg;base64,{base64.b64encode(file.read()).decode("utf-8")}' if file else ""
        data = {'name': request.form.get('name'), 'quantity': int(request.form.get('quantity', 0)), 'price': float(request.form.get('price', 0.0)), 'company_id_text': company_code, 'product-images': encoded_string}
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
            supabase.storage.from_("products").upload(filename, file.read(), {"content-type": file.content_type})
            update_data["product-images"] = supabase.storage.from_("products").get_public_url(filename)
        supabase.table('inventory').update(update_data).eq("id", product_id).eq("company_id_text", company_code).execute()
    res = supabase.table("inventory").select("*").eq("company_id_text", company_code).execute()
    return render_template('inventory_management.html', inventory=res.data or [])

@app.route('/edit_product/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    company_code = session.get('company_code')
    res = supabase.table("inventory").select("*").eq("id", id).eq("company_id_text", company_code).execute()
    product = res.data[0] if res.data else None
    if request.method == 'POST':
        supabase.table("inventory").update({"name": request.form.get('name'), "quantity": int(request.form.get('quantity')), "price": float(request.form.get('price'))}).eq("id", id).execute()
        return redirect(url_for('products'))
    return render_template('edit_product.html', product=product)

@app.route('/delete_product/<int:id>', methods=['POST'])
@login_required
def delete_product(id):
    supabase.table("inventory").delete().eq("id", id).execute()
    return redirect(url_for('products'))

@app.route('/delete_order/<int:id>', methods=['POST'])
@login_required
def delete_order(id):
    supabase.table("orders").delete().eq("id", id).eq("company_code", session.get('company_code')).execute()
    return redirect(url_for('orders'))

@app.route('/orders', methods=['GET', 'POST'])
@login_required
def orders():
    company_code = session.get('company_code')
    res_settings = supabase.table("settings").select("currency, telegram_token, telegram_chat_id").eq("company_code", company_code).execute()
    settings_info = res_settings.data[0] if res_settings.data else {}
    if request.method == 'POST':
        product_name = request.form.get('product_name')
        requested_qty = int(request.form.get('quantity', 0))
        data = {"customer_name": request.form.get('customer_name'), "customer_phone": request.form.get('customer_phone'), "product_name": product_name, "quantity": requested_qty, "total_price": float(request.form.get('price', 0.0)), "company_code": company_code, "status": "قيد الانتظار"}
        supabase.table("orders").insert(data).execute()
        token, chat_id = settings_info.get('telegram_token'), settings_info.get('telegram_chat_id')
        if token and chat_id:
            send_telegram_alert_by_token(token, chat_id, f"🛒 طلبية جديدة! المنتج: {product_name}")
            products_res = supabase.table("inventory").select("id, quantity").eq("name", product_name).eq("company_id_text", company_code).execute()
            if products_res.data:
                product = products_res.data[0]
                new_qty = max(0, product['quantity'] - requested_qty)
                supabase.table("inventory").update({"quantity": new_qty}).eq("id", product['id']).execute()
        return redirect(url_for('orders'))
    res = supabase.table("orders").select("*").eq("company_code", company_code).execute()
    return render_template('orders_dashboard.html', orders=res.data or [], currency=settings_info.get('currency', ''))

@app.route('/webhook_instagram', methods=['GET', 'POST'])
def webhook_instagram():
    if request.method == 'GET': return request.args.get('hub.challenge')
    data = request.json
    try:
        for entry in data.get('entry', []):
            page_id = entry.get('id')
            for messaging_event in entry.get('messaging', []):
                if 'message' in messaging_event and 'text' in messaging_event['message']:
                    msg = messaging_event['message']['text']
                    sender_id = messaging_event['sender']['id']
                    res = supabase.table("settings").select("company_code, telegram_token, telegram_chat_id, instagram_token").eq("instagram_page_id", page_id).execute()
                    if res.data:
                        s = res.data[0]
                        send_telegram_alert_by_token(s['telegram_token'], s['telegram_chat_id'], f"رسالة جديدة: {msg}")
                        reply_text = client.models.generate_content(model='gemini-2.0-flash', contents=msg).text
                        response = send_instagram_reply(s['instagram_token'], sender_id, reply_text)
                        if response.status_code != 200:
                            new_token = refresh_token_for_company(s['company_code'], s['instagram_token'])
                            send_instagram_reply(new_token, sender_id, reply_text)
        return 'OK', 200
    except Exception as e:
        print(f"Webhook Error: {e}")
        return 'OK', 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
