import os
from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'chaima_secure_2026'

# ربط Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# 1. تسجيل الدخول
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

# 2. لوحة التحكم مع تحليل البيانات
@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    
    # جلب المبيعات
    sales = supabase.table("sales").select("*").eq("company_id", session['company_id']).execute().data
    total_revenue = sum(float(item['amount']) for item in sales)
    
    # جلب المصاريف (للمدير فقط)
    expenses = []
    if session['role'] == 'admin':
        expenses = supabase.table("expenses").select("*").eq("company_id", session['company_id']).execute().data
        
    return render_template('users.html', sales=sales, total_revenue=total_revenue, expenses=expenses, role=session['role'])

# 3. تسجيل بيعة جديدة
@app.route('/add_sale', methods=['POST'])
def add_sale():
    if 'user' not in session: return "Unauthorized", 401
    
    supabase.table("sales").insert({
        "company_id": session['company_id'],
        "customer_name": request.form.get('customer_name'),
        "phone": request.form.get('phone'),
        "product_name": request.form.get('product_name'),
        "amount": float(request.form.get('amount')),
        "created_at": datetime.now().isoformat()
    }).execute()
    return redirect(url_for('dashboard'))

# 4. تسجيل مصروف (للمدير فقط)
@app.route('/add_expense', methods=['POST'])
def add_expense():
    if session.get('role') != 'admin': return "غير مصرح لك", 403
    supabase.table("expenses").insert({
        "company_id": session['company_id'],
        "name": request.form.get('expense_name'),
        "amount": float(request.form.get('expense_amount'))
    }).execute()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
