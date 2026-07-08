from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)
# ضروري جداً لتشغيل نظام الجلسات (Sessions)
app.secret_key = 'your_very_secret_key_here' 

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- نظام تسجيل الدخول ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        # التحقق من المستخدم في جدول users
        user = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
        if user.data:
            session['user_id'] = user.data[0]['id']
            session['company_id'] = user.data[0]['company_id'] # عزل البيانات
            return redirect(url_for('dashboard'))
        return "بيانات الدخول غير صحيحة"
    return render_template('login.html')

# --- الطلبيات (مع عزل بيانات الشركة) ---

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']

    if request.method == 'POST':
        data = {
            "customer_name": request.form.get("customer_name"),
            "customer_phone": request.form.get("customer_phone"),
            "product_name": request.form.get("product_name"),
            "total_price": float(request.form.get("total_price", 0)),
            "company_id": comp_id, # الربط ضروري
            "created_at": datetime.now().isoformat()
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))

    # جلب بيانات الشركة الحالية فقط
    orders_data = supabase.table("orders").select("*").eq("company_id", comp_id).execute().data
    total = sum(float(o.get('total_price', 0)) for o in orders_data)
    return render_template('orders_dashboard.html', orders=orders_data, total=total)

# --- الإحصائيات (مع المنحنيات المرتبة) ---

@app.route('/stats')
def stats():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    
    orders = supabase.table("orders").select("*").eq("company_id", comp_id).execute().data
    
    # قوالب بيانات ثابتة
    daily = {day: 0 for day in ['السبت', 'الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة']}
    monthly = {month: 0 for month in ['جانفي', 'فيفري', 'مارس', 'أفريل', 'ماي', 'جوان', 'جويلية', 'أوت', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']}
    
    days_map = {'Monday': 'الاثنين', 'Tuesday': 'الثلاثاء', 'Wednesday': 'الأربعاء', 'Thursday': 'الخميس', 'Friday': 'الجمعة', 'Saturday': 'السبت', 'Sunday': 'الأحد'}
    months_map = {'January': 'جانفي', 'February': 'فيفري', 'March': 'مارس', 'April': 'أفريل', 'May': 'ماي', 'June': 'جوان', 'July': 'جويلية', 'August': 'أوت', 'September': 'سبتمبر', 'October': 'أكتوبر', 'November': 'نوفمبر', 'December': 'ديسمبر'}

    for order in orders:
        dt = datetime.strptime(order.get('created_at', datetime.now().isoformat())[:10], '%Y-%m-%d')
        d, m = days_map.get(dt.strftime('%A')), months_map.get(dt.strftime('%B'))
        if d in daily: daily[d] += float(order.get('total_price', 0))
        if m in monthly: monthly[m] += float(order.get('total_price', 0))
        
    return render_template('stats.html', daily=daily, monthly=monthly)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
