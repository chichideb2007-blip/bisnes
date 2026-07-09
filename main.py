from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
from datetime import datetime
import json

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
            if user.data and len(user.data) > 0:
                # تخزين company_id في الجلسة لتمييز المستخدم
                session['company_id'] = str(user.data[0]['company_id'])
                return redirect(url_for('dashboard'))
            return "بيانات الدخول خاطئة"
        except Exception as e:
            return f"خطأ في الاتصال: {e}"
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # عند التسجيل، نتأكد أن الشركة تأخذ معرفاً خاصاً بها
            new_user = {
                "email": request.form.get('email'),
                "password": request.form.get('password'),
                "company_id": request.form.get('company_id')
            }
            supabase.table("users").insert(new_user).execute()
            return "تم التسجيل بنجاح! <a href='/login'>العودة لتسجيل الدخول</a>"
        except Exception as e:
            return f"خطأ في التسجيل: {e}"
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id'] # المستخدم الحالي
    
    if request.method == 'POST':
        try:
            # إضافة طلبية مرتبطة حصراً بـ comp_id الحالي
            new_order = {
                "customer_name": request.form.get("customer_name"),
                "customer_phone": request.form.get("customer_phone"),
                "product_name": request.form.get("product"),
                "total_price": float(request.form.get("price", 0)), 
                "company_id_text": comp_id, # الربط العازل
                "status": "قيد الانتظار"
            }
            supabase.table("orders").insert(new_order).execute()
            return redirect(url_for('orders'))
        except Exception as e:
            return f"خطأ في الإضافة: {e}"
    
    # جلب الطلبيات الخاصة بهذه الشركة فقط (عزل تام)
    response = supabase.table("orders").select("*").eq("company_id_text", comp_id).execute()
    return render_template('orders_dashboard.html', orders=response.data or [])

@app.route('/delete_order/<int:order_id>')
def delete_order(order_id):
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    try:
        # التأكد أن الحذف يتم فقط إذا كانت الطلبية تنتمي لهذه الشركة (لحماية البيانات)
        supabase.table("orders").delete().eq("id", order_id).eq("company_id_text", comp_id).execute()
    except Exception as e:
        return f"خطأ في الحذف: {e}"
    return redirect(url_for('orders'))

@app.route('/stats')
def stats():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    try:
        # جلب الإحصائيات الخاصة بهذه الشركة فقط
        response = supabase.table("orders").select("*").eq("company_id_text", comp_id).execute()
        orders = response.data or []

        days_names = ["السبت", "الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
        months_names = ["جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان", "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
        
        daily_stats = {d: 0 for d in days_names}
        monthly_stats = {m: 0 for m in months_names}
        yearly_stats = {} 
        
        daily_total = 0
        today = datetime.now().date()

        for o in orders:
            created_at_str = o.get('created_at', datetime.now().isoformat())
            created_at = datetime.fromisoformat(created_at_str.replace('Z', ''))
            price = float(o.get('total_price', 0))
            
            daily_stats[days_names[created_at.weekday()]] += price
            monthly_stats[months_names[created_at.month - 1]] += price
            
            year = str(created_at.year)
            yearly_stats[year] = yearly_stats.get(year, 0) + price
            
            if created_at.date() == today:
                daily_total += price

        return render_template('stats.html', 
                               daily=json.dumps(daily_stats), 
                               monthly=json.dumps(monthly_stats), 
                               yearly=json.dumps(dict(sorted(yearly_stats.items()))), 
                               daily_total=daily_total)
    except Exception as e:
        return f"خطأ في الإحصائيات: {e}"

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
