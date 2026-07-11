from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from google import genai
import os, uuid, requests

app = Flask(__name__)
# تأكدي من إعداد متغير البيئة SECRET_KEY في موقع Render
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

# إعداد Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# إعداد العميل لـ Gemini
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- دالة الذكاء الاصطناعي ---
def get_gemini_response(company_id, user_message):
    products = supabase.table("inventory").select("name, price, quantity").eq("company_id", company_id).execute()
    prod_list = str(products.data)
    system_instruction = f"أنت مساعد مبيعات ذكي لمتجر جزائري. قائمة منتجاتنا: {prod_list}. أجب الزبون بنفس اللغة."
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=system_instruction + "\nرسالة الزبون: " + user_message
    )
    return response.text

# --- المسارات الرئيسية ---
@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

# --- 1. إدارة الطلبيات ---
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'company_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        supabase.table("orders").insert({
            "company_id": session['company_id'],
            "customer_name": request.form.get('customer_name'),
            "phone": request.form.get('phone'),
            "product_name": request.form.get('product_name'),
            "price": request.form.get('price')
        }).execute()
        return redirect(url_for('orders'))
    res = supabase.table("orders").select("*").eq("company_id", session['company_id']).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

# --- 2. الإحصائيات ---
@app.route('/statistics')
def stats():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('stats.html')

# --- 3. إدارة المنتجات ---
@app.route('/products', methods=['GET', 'POST'])
def products():
    if 'company_id' not in session: return redirect(url_for('login'))
    
    if request.method == 'POST':
        supabase.table("inventory").insert({
            "company_id": session['company_id'],
            "name": request.form.get('name'),
            "quantity": request.form.get('quantity'),
            "price": request.form.get('price')
        }).execute()
        return redirect(url_for('products'))
    
    res = supabase.table("inventory").select("*").eq("company_id", session['company_id']).execute()
    return render_template('products.html', products=res.data or [])

# --- مسار حذف المنتج ---
@app.route('/delete_product/<int:product_id>')
def delete_product(product_id):
    if 'company_id' not in session: return redirect(url_for('login'))
    supabase.table("inventory").delete().eq("id", product_id).execute()
    return redirect(url_for('products'))

# --- 4. الإعدادات ---
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'company_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        supabase.table("companies").update({
            "store_name": request.form.get('store_name'),
            "telegram_token": request.form.get('telegram_token')
        }).eq("id", session['company_id']).execute()
        return redirect(url_for('settings'))
    res = supabase.table("companies").select("*").eq("id", session['company_id']).single().execute()
    return render_template('settings.html', settings=res.data)

# --- مسارات التسجيل والدخول وخروج ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        supabase.table("companies").insert({
            "email": request.form.get('email'),
            "password": request.form.get('password'),
            "store_name": request.form.get('store_name'),
            "instagram_token": str(uuid.uuid4()),
            "telegram_token": str(uuid.uuid4())
        }).execute()
        return "تم التسجيل بنجاح!"
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        res = supabase.table("companies").select("*").eq("email", request.form.get('email')).single().execute()
        if res.data and res.data['password'] == request.form.get('password'):
            session['company_id'] = res.data['id']
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('company_id', None) # مسح الجلسة عند تسجيل الخروج
    return redirect(url_for('login'))

# --- مسار الـ Webhook (للذكاء الاصطناعي) ---
@app.route('/webhook/<token>', methods=['POST'])
def telegram_webhook(token):
    company = supabase.table("companies").select("*").eq("telegram_token", token).single().execute()
    if not company.data: return "Invalid Token", 403
    data = request.get_json()
    if 'message' in data:
        chat_id = data['message']['chat']['id']
        ai_reply = get_gemini_response(company.data['id'], data['message'].get('text', ''))
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": ai_reply})
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)
