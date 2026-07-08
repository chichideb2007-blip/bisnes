from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
        if user.data:
            session['company_id'] = str(user.data[0]['company_id'])
            return redirect(url_for('dashboard'))
        return "بيانات الدخول خاطئة"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    if request.method == 'POST':
        new_order = {
            "customer_name": request.form.get("customer_name"),
            "product": request.form.get("product"),
            "price": float(request.form.get("price", 0)),
            "company_id_text": comp_id
        }
        supabase.table("orders").insert(new_order).execute()
        return redirect(url_for('orders'))
    
    response = supabase.table("orders").select("*").eq("company_id_text", comp_id).execute()
    return render_template('orders_dashboard.html', orders=response.data or [])

@app.route('/stats')
def stats():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = str(session['company_id'])
    response = supabase.table("orders").select("*").eq("company_id_text", comp_id).execute()
    orders = response.data or []

    # تهيئة البيانات
    days = ["السبت", "الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
    months = ["جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان", "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
    
    daily = {d: 0 for d in days}
    monthly = {m: 0 for m in months}
    yearly = defaultdict(float)

    for o in orders:
        # إذا لم يوجد تاريخ، نستخدم تاريخ اليوم للطلب
        date = datetime.now() 
        price = float(o.get('price', 0))
        daily[days[date.weekday()]] += price
        monthly[months[date.month - 1]] += price
        yearly[str(date.year)] += price

    return render_template('stats.html', daily=daily, monthly=monthly, yearly=dict(yearly), orders=orders)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
