from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# التأكد من تحميل المتغيرات
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- المسارات ---

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    # جلب المستخدم
    user = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
    
    if user.data:
        # تخزين الـ UUID كما هو من قاعدة البيانات (حتى لا يحدث خطأ في النوع)
        session['company_id'] = user.data[0]['company_id'] 
        return redirect(url_for('dashboard'))
    return "بيانات الدخول خاطئة"

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    
    if request.method == 'POST':
        # حفظ طلبية
        new_order = {
            "customer_name": request.form.get("customer_name"),
            "product": request.form.get("product"),
            "price": request.form.get("price"),
            "company_id": comp_id # نرسل الـ UUID الأصلي المستخرج من الجلسة
        }
        supabase.table("orders").insert(new_order).execute()
        return redirect(url_for('orders'))
    
    # جلب الطلبيات
    response = supabase.table("orders").select("*").eq("company_id", comp_id).execute()
    return render_template('orders_dashboard.html', orders=response.data or [])

@app.route('/stats')
def stats():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    
    # جلب الإحصائيات (تأكدنا من وجود [] في حالة الفراغ لمنع الانهيار)
    response = supabase.table("orders").select("*").eq("company_id", comp_id).execute()
    return render_template('stats.html', orders=response.data or [])

# ... باقي المسارات (home, dashboard, logout) كما هي لديك
