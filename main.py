from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
from datetime import datetime

app = Flask(__name__)

# تأكدي من إدخال SECRET_KEY في إعدادات Render (Environment Variables)
# إذا لم يعمل الموقع، تأكدي أن هذا المفتاح ليس فارغاً
app.secret_key = os.environ.get("SECRET_KEY", "a_very_secret_key_123")

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
            # التحقق من المستخدم
            user = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
            if user.data and len(user.data) > 0:
                session['company_id'] = str(user.data[0]['company_id'])
                return redirect(url_for('dashboard'))
            return "بيانات الدخول خاطئة"
        except Exception as e:
            return f"<h1>خطأ في تسجيل الدخول:</h1> <pre>{str(e)}</pre>"
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            new_user = {
                "email": request.form.get('email'),
                "password": request.form.get('password'),
                "company_id": request.form.get('company_id')
            }
            supabase.table("users").insert(new_user).execute()
            return "تم التسجيل بنجاح! <a href='/login'>العودة لتسجيل الدخول</a>"
        except Exception as e:
            return f"<h1>خطأ في التسجيل:</h1> <pre>{str(e)}</pre>"
    return render_template('register.html')

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
            # البيانات التي سيتم إدخالها - تأكدي أن هذه الأسماء موجودة في جدول Supabase
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
            return f"<h1>خطأ في إضافة الطلبية:</h1> <pre>{str(e)}</pre>"
    
    try:
        response = supabase.table("orders").select("*").eq("company_id_text", comp_id).execute()
        return render_template('orders_dashboard.html', orders=response.data or [])
    except Exception as e:
        return f"<h1>خطأ في تحميل الطلبيات:</h1> <pre>{str(e)}</pre>"

@app.route('/delete_order/<int:order_id>')
def delete_order(order_id):
    if 'company_id' not in session: return redirect(url_for('login'))
    try:
        supabase.table("orders").delete().eq("id", order_id).execute()
    except Exception as e:
        return f"خطأ في الحذف: {e}"
    return redirect(url_for('orders'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
