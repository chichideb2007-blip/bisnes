from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
from datetime import datetime

app = Flask(__name__)
# تأكدي من إعداد المفتاح السري في إعدادات Render كمتغير بيئي (SECRET_KEY)
app.secret_key = os.environ.get("SECRET_KEY", "default_secret_key")

# إعداد Supabase
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
        try:
            # البحث عن المستخدم
            user = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
            if user.data:
                # تخزين الـ UUID كما هو من قاعدة البيانات
                session['company_id'] = user.data[0]['company_id']
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
        # حفظ الطلبية - التأكد أن company_id يرسل كـ UUID مطابق لما في القاعدة
        order_data = {
            "customer_name": request.form.get("customer_name"),
            "product": request.form.get("product"),
            "price": float(request.form.get("price", 0)),
            "company_id": comp_id 
        }
        supabase.table("orders").insert(order_data).execute()
        return redirect(url_for('orders'))

    # جلب الطلبات المرتبطة بالـ UUID
    response = supabase.table("orders").select("*").eq("company_id", comp_id).execute()
    return render_template('orders_dashboard.html', orders=response.data)

@app.route('/stats')
def stats():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    response = supabase.table("orders").select("*").eq("company_id", comp_id).execute()
    return render_template('stats.html', orders=response.data)

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
