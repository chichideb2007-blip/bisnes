from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
import requests
import uuid
import google.generativeai as genai

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# إعداد Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# --- دالة الذكاء الاصطناعي (Gemini) ---
def get_gemini_response(company_id, user_message):
    # جلب منتجات الشركة
    products = supabase.table("inventory").select("name, price, quantity").eq("company_id", company_id).execute()
    prod_list = str(products.data)
    
    system_instruction = f"""
    أنت مساعد مبيعات ذكي لمتجر جزائري.
    هذه قائمة منتجاتنا وأسعارها: {prod_list}.
    - أجب الزبون بنفس اللغة التي استخدمها (دارجة، فرنسية، أو مزيج).
    - إذا سأل عن السعر أو التوفر، أجب بدقة بناءً على القائمة.
    - إذا أراد الزبون الشراء، اطلب منه (الاسم، العنوان، رقم الهاتف).
    - لا تقترح أي منتج غير موجود في القائمة.
    """
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(system_instruction + "\nرسالة الزبون: " + user_message)
    return response.text

# --- دالة إرسال التنبيه للمدير ---
def send_telegram_notification(comp_id, order_details):
    try:
        company = supabase.table("companies").select("*").eq("id", comp_id).single().execute()
        if not company.data: return
        
        token = company.data.get('telegram_token')
        chat_id = company.data.get('manager_phone')
        url_api = f"https://api.telegram.org/bot{token}/sendMessage"
        body = f"🔔 طلبية جديدة!\n👤 العميل: {order_details['customer_name']}\n📦 المنتج: {order_details['product_name']}"
        requests.post(url_api, json={"chat_id": chat_id, "text": body}, timeout=5)
    except Exception as e:
        print(f"Error: {e}")

# --- مسار الـ Webhook (يستقبل رسائل التيلجرام) ---
@app.route('/webhook/<token>', methods=['POST'])
def telegram_webhook(token):
    company = supabase.table("companies").select("*").eq("telegram_token", token).single().execute()
    if not company.data: return "Invalid Token", 403
    
    comp_id = company.data['id']
    data = request.get_json()
    chat_id = data['message']['chat']['id']
    user_text = data['message'].get('text', '')
    
    # الحصول على رد Gemini
    ai_reply = get_gemini_response(comp_id, user_text)
    
    # إرسال الرد للعميل
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                  json={"chat_id": chat_id, "text": ai_reply})
    return "OK", 200

# --- مسارات لوحة التحكم (Dashboard) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # أضيفي منطق التحقق من الدخول هنا
        return "تم تسجيل الدخول"
    return render_template('login.html')

@app.route('/products')
def products():
    if 'company_id' not in session: return redirect(url_for('login'))
    response = supabase.table("inventory").select("*").eq("company_id", session['company_id']).execute()
    return render_template('products.html', products=response.data or [])

if __name__ == '__main__':
    app.run(debug=True)
