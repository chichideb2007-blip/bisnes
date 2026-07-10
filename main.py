from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
import requests
from datetime import datetime
import json
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- 1. مسار الـ Webhook الجديد لاستقبال رسائل تيلجرام ---
@app.route('/webhook/<token>', methods=['POST'])
def telegram_webhook(token):
    # جلب بيانات الشركة بناءً على التوكن المرسل في الرابط
    company = supabase.table("companies").select("*").eq("telegram_token", token).single().execute()
    
    if not company.data:
        return "Invalid Token", 403
    
    comp_id = company.data['id']
    data = request.get_json()
    
    # هنا ستكون منطق الذكاء الاصطناعي (AI Logic)
    # يمكنكِ جلب المنتجات لهذه الشركة فقط كالتالي:
    # products = supabase.table("inventory").select("*").eq("company_id", comp_id).execute()
    
    return "OK", 200

# --- 2. دالة إرسال التنبيهات (تم تعديلها لتأخذ الـ comp_id) ---
def send_telegram_notification(comp_id, order_details):
    try:
        # جلب بيانات الشركة
        company = supabase.table("companies").select("*").eq("id", comp_id).single().execute()
        if not company.data: return
        
        telegram_token = company.data.get('telegram_token')
        chat_id = company.data.get('manager_phone')
        store_name = company.data.get('store_name', 'متجرك')
        
        url_api = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        body_text = (f"🔔 طلبية جديدة في: {store_name}\n\n"
                     f"👤 العميل: {order_details['customer_name']}\n"
                     f"📦 المنتج: {order_details['product_name']}")
        
        requests.post(url_api, json={"chat_id": chat_id, "text": body_text}, timeout=5)
    except Exception as e:
        print(f"Error: {e}")

# --- المسارات التقليدية (Login, Dashboard, Products...) ---
# (استخدمي نفس المسارات التي كانت في كودك السابق، فهي صحيحة تماماً)
# تأكدي فقط من تحديث المسارات التي تستخدم comp_id لتطابق هيكل قاعدة البيانات الجديد

@app.route('/products', methods=['GET', 'POST'])
def products():
    # تأكدي أنكِ تستخدمين comp_id المستمد من جدول companies الجديد
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    
    # ... بقية منطق المنتجات ...
    response = supabase.table("inventory").select("*").eq("company_id", comp_id).execute()
    return render_template('products.html', products=response.data or [])

# ... (باقي المسارات الخاصة بكِ) ...

if __name__ == '__main__':
    app.run(debug=True)
