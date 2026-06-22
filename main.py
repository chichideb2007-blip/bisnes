import os
from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'chaima_secure_2026'

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    
    # جلب المصاريف (موجود عندك)
    expenses = supabase.table("expenses").select("*").eq("company_id", session['company_id']).execute().data
    
    # جلب المبيعات (إذا كان الجدول غير موجود، سيعطي قائمة فارغة بدل أن يغلق الموقع)
    try:
        sales = supabase.table("sales").select("*").eq("company_id", session['company_id']).execute().data
    except:
        sales = [] # إذا لم تنشئي الجدول بعد، لن يتوقف الموقع
        
    total_revenue = sum(float(item['amount']) for item in sales) if sales else 0
    
    return render_template('users.html', sales=sales, total_revenue=total_revenue, expenses=expenses, role=session.get('role'))

# ... باقي الدوال (login, add_sale, add_expense) تبقى كما هي في الكود السابق ...
