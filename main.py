from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from google import genai
import os
import requests
import uuid
import json

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# إعداد العميل لـ Gemini
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- المسار الرئيسي ---
@app.route('/')
def home():
    return redirect(url_for('register'))

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

# --- مسار التسجيل ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password') 
        store_name = request.form.get('store_name')
        try:
            supabase.table("companies").insert({
                "email": email, "password": password, "store_name": store_name,
                "instagram_token": str(uuid.uuid4()), "telegram_token": str(uuid.uuid4())
            }).execute()
            return "تم التسجيل بنجاح! يمكنك الآن تسجيل الدخول."
        except Exception as e:
            return f"خطأ: {str(e)}", 400
    return render_template('register.html')

# --- مسار تسجيل الدخول ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        response = supabase.table("companies").select("*").eq("email", email).single().execute()
        if response.data and response.data['password'] == password:
            session['company_id'] = response.data['id']
            return redirect(url_for('inventory'))
        return "بيانات الدخول غير صحيحة!", 401
    return render_template('login.html')

# --- مسار إدارة المخزون ---
@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if 'company_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        supabase.table("inventory").insert({
            "company_id": session['company_id'],
            "name": request.form.get('name'),
            "quantity": request.form.get('quantity'),
            "price": request.form.get('price')
        }).execute()
        return redirect(url_for('inventory'))
    
    response = supabase.table("inventory").select("*").eq("company_id", session['company_id']).execute()
    return render_template('products.html', products=response.data or [])

# --- مسار البحث ---
@app.route('/search_products', methods=['GET'])
def search_products():
    if 'company_id' not in session: return redirect(url_for('login'))
    query = request.args.get('q')
    response = supabase.table("inventory").select("*").eq("company_id", session['company_id']).ilike("name", f"%{query}%").execute()
    return render_template('products.html', products=response.data or [])

# --- مسار الحذف ---
@app.route('/delete_product/<int:product_id>')
def delete_product(product_id):
    if 'company_id' not in session: return redirect(url_for('login'))
    supabase.table("inventory").delete().eq("id", product_id).execute()
    return redirect(url_for('inventory'))

if __name__ == '__main__':
    app.run(debug=True)
