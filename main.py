from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from google import genai
import os, json

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- الدوال المساعدة ---
def send_telegram_alert(token, chat_id, message):
    # كود إرسال التنبيه لتلجرام
    pass

# --- المسارات الرئيسية ---

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# 1. إدارة المخزن
@app.route('/products', methods=['GET', 'POST'])
def products():
    if request.method == 'POST':
        supabase.table("inventory").insert({
            "company_id": session['company_id'],
            "name": request.form.get('name'),
            "quantity": int(request.form.get('quantity') or 0),
            "price": float(request.form.get('price') or 0)
        }).execute()
        return redirect(url_for('products'))
    res = supabase.table("inventory").select("*").eq("company_id", session['company_id']).execute()
    return render_template('products.html', products=res.data or [])

# 2. إدارة الطلبيات (مع إرسال تنبيه تلجرام)
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        # حفظ الطلبية
        supabase.table("orders").insert({
            "company_id": session['company_id'],
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('customer_phone'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('total_price') or 0),
            "status": "قيد الانتظار"
        }).execute()
        
        # إرسال تنبيه تلجرام للمدير (بناءً على إعداداته)
        settings = supabase.table("companies").select("telegram_token, manager_phone").eq("id", session['company_id']).execute()
        if settings.data:
            # هنا نستدعي دالة التنبيه (send_telegram_alert)
            pass
            
        return redirect(url_for('orders'))
    res = supabase.table("orders").select("*").eq("company_id", session['company_id']).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

# 3. الإحصائيات
@app.route('/stats')
def stats():
    # جلب الطلبيات فقط الخاصة بهذه الشركة (عزل البيانات)
    res = supabase.table("orders").select("*").eq("company_id", session['company_id']).execute()
    return render_template('stats.html', orders=res.data or [])

# 4. دمج انستقرام مع جيميني (AI Chat)
@app.route('/ai_chat', methods=['POST'])
def ai_chat():
    user_msg = request.form.get('message')
    # الربط مع Gemini
    response = client.models.generate_content(model="gemini-1.5-flash", contents=user_msg)
    return {"reply": response.text}

# 5. الإعدادات (عزل المدراء)
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    # المدراء يشوفوا إعدادات شركتهم فقط بفضل eq("id", session['company_id'])
    res = supabase.table("companies").select("*").eq("id", session['company_id']).execute()
    return render_template('settings.html', settings=res.data[0] if res.data else {})

if __name__ == '__main__':
    app.run(debug=True)
