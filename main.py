from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from google import genai
import os
import requests
import uuid
import json

app = Flask(__name__)
# تأكدي من إعداد SECRET_KEY في إعدادات Render
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# إعداد العميل الجديد لـ Gemini
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- المسار الرئيسي ---
@app.route('/')
def home():
    return redirect(url_for('register'))

# --- دالة الذكاء الاصطناعي (Gemini) ---
def get_gemini_response(company_id, user_message):
    products = supabase.table("inventory").select("name, price, quantity").eq("company_id", company_id).execute()
    prod_list = str(products.data)
    
    system_instruction = f"""
    أنت مساعد مبيعات ذكي لمتجر جزائري.
    قائمة منتجاتنا: {prod_list}.
    - أجب الزبون بنفس اللغة التي استخدمها (دارجة، فرنسية، أو مزيج).
    - إذا أراد الشراء، اطلب منه (الاسم، العنوان، رقم الهاتف).
    - لا تقترح أي منتج غير موجود في القائمة.
    """
    
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=system_instruction + "\nرسالة الزبون: " + user_message
    )
    return response.text

# --- مسار التسجيل ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password') 
        store_name = request.form.get('store_name')
        
        try:
            supabase.table("companies").insert({
                "email": email,
                "password": password,
                "store_name": store_name,
                "instagram_token": str(uuid.uuid4()),
                "telegram_token": str(uuid.uuid4())
            }).execute()
            return "تم تسجيل شركتك بنجاح! يمكنك الآن تسجيل الدخول."
        except Exception as e:
            return f"حدث خطأ أثناء التسجيل: {str(e)}", 400
            
    return render_template('register.html')

# --- مسار الـ Webhook ---
@app.route('/webhook/<token>', methods=['POST'])
def telegram_webhook(token):
    company = supabase.table("companies").select("*").eq("telegram_token", token).single().execute()
    if not company.data: return "Invalid Token", 403
    
    comp_id = company.data['id']
    data = request.get_json()
    
    if 'message' not in data: return "OK", 200
    
    chat_id = data['message']['chat']['id']
    user_text = data['message'].get('text', '')
    
    ai_reply = get_gemini_response(comp_id, user_text)
    
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                  json={"chat_id": chat_id, "text": ai_reply})
    return "OK", 200

# --- لوحة التحكم ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@app.route('/products')
def products():
    if 'company_id' not in session: return redirect(url_for('login'))
    response = supabase.table("inventory").select("*").eq("company_id", session['company_id']).execute()
    return render_template('products.html', products=response.data or [])

if __name__ == '__main__':
    app.run(debug=True)
