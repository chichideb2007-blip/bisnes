from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- المسارات ---

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            user = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
            if user.data:
                session['company_id'] = str(user.data[0]['company_id'])
                return redirect(url_for('dashboard'))
            return "بيانات الدخول خاطئة"
        except Exception as e:
            return f"خطأ في الاتصال: {e}"
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
        try:
            # استخدام الأسماء الصحيحة كما هي في جدول Supabase
            new_order = {
                "customer_name": request.form.get("customer_name"),
                "customer_phone": request.form.get("customer_phone"),
                "product_name": request.form.get("product"),
                "total_price": float(request.form.get("price", 0)), 
                "company_id_text": comp_id,
                "status": "قيد الانتظار"
            }
            supabase.table("orders").insert(new_order).execute()
            return redirect(url_for('orders'))
        except Exception as e:
            return f"خطأ في إضافة الطلبية: {e}"
    
    response = supabase.table("orders").select("*").eq("company_id_text", comp_id).execute()
    return render_template('orders_dashboard.html', orders=response.data or [])

# مسار حذف الطلبية (يحل مشكلة 404)
@app.route('/delete_order/<int:order_id>')
def delete_order(order_id):
    if 'company_id' not in session: return redirect(url_for('login'))
    supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect(url_for('orders'))

@app.route('/stats')
def stats():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    
    try:
        response = supabase.table("orders").select("*").eq("company_id_text", comp_id).execute()
        orders = response.data or []

        days = ["السبت", "الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
        months = ["جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان", "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
        
        daily = {d: 0 for d in days}
        monthly = {m: 0 for m in months}
        yearly = {}

        for o in orders:
            price = float(o.get('total_price', 0)) # مطابقة اسم العمود
            date_val = datetime.now() 
            
            daily[days[date_val.weekday()]] += price
            monthly[months[date_val.month - 1]] += price
            year = str(date_val.year)
            yearly[year] = yearly.get(year, 0) + price

        return render_template('stats.html', daily=daily, monthly=monthly, yearly=yearly, orders=orders)
    except Exception as e:
        return f"خطأ في تحميل الإحصائيات: {e}"

@app.route('/settings')
def settings():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('settings.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
