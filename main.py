import os
from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'chaima_secret_key_2026'

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- لوحة التحكم (التي تعرض تحليل البيانات للمدير) ---
@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    
    # جلب المبيعات للتحليل
    sales = supabase.table("sales").select("*").eq("company_id", session['company_id']).execute().data
    
    # حساب إجمالي الدخل اليومي
    total_revenue = sum(float(item['amount']) for item in sales)
    
    return render_template('users.html', sales=sales, total_revenue=total_revenue, role=session.get('role'))

# --- تسجيل بيعة جديدة (الذكاء في تحليل المنتج) ---
@app.route('/add_sale', methods=['POST'])
def add_sale():
    if 'user' not in session: return "Unauthorized", 401
    
    # بيانات الزبون والطلب
    name = request.form.get('customer_name')
    phone = request.form.get('phone')
    product_name = request.form.get('product_name')
    amount = request.form.get('amount')
    
    supabase.table("sales").insert({
        "company_id": session['company_id'],
        "customer_name": name,
        "phone": phone,
        "product_name": product_name,
        "amount": float(amount),
        "created_at": datetime.now().isoformat()
    }).execute()
    
    return redirect(url_for('dashboard'))

# --- تسجيل الدخول ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
        if user.data:
            session['user'] = username
            session['company_id'] = user.data[0]['company_id']
            session['role'] = user.data[0].get('role', 'employee')
            return redirect(url_for('dashboard'))
    return render_template('login.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
