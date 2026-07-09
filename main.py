from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

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
            user = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
            if user.data and len(user.data) > 0:
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
    comp_id = session['company_id']
    
    if request.method == 'POST':
        try:
            # البيانات التي سيتم إدخالها
            data = {
                "customer_name": request.form.get("customer_name"),
                "customer_phone": request.form.get("customer_phone"),
                "product_name": request.form.get("product"),
                "total_price": float(request.form.get("price", 0)), 
                "company_id_text": comp_id,
                "status": "قيد الانتظار"
            }
            supabase.table("orders").insert(data).execute()
            return redirect(url_for('orders'))
        except Exception as e:
            # هذا الجزء سيعرض الخطأ الحقيقي على الشاشة بدلاً من 500
            return f"<h1>خطأ في قاعدة البيانات:</h1> <pre>{str(e)}</pre>"
    
    response = supabase.table("orders").select("*").eq("company_id_text", comp_id).execute()
    return render_template('orders_dashboard.html', orders=response.data or [])

@app.route('/delete_order/<int:order_id>')
def delete_order(order_id):
    if 'company_id' not in session: return redirect(url_for('login'))
    try:
        supabase.table("orders").delete().eq("id", order_id).execute()
    except Exception as e:
        return f"خطأ في الحذف: {e}"
    return redirect(url_for('orders'))

if __name__ == '__main__':
    app.run(debug=True)
