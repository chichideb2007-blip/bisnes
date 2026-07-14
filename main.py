from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__, template_folder='templates')
# تأكدي أن SECRET_KEY مضبوط في إعدادات Render
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

# إعداد Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            # محاولة الاتصال بـ Supabase
            res = supabase.table("companies").select("*").eq("email", email).execute()
            
            # طباعة البيانات للـ Logs للتأكد (ستظهر في سجلات Render)
            print(f"DEBUG: Data found for {email}: {res.data}") 
            
            if res.data and res.data[0].get('password') == password:
                session['company_id'] = res.data[0]['id']
                return redirect(url_for('dashboard'))
            else:
                return "البريد الإلكتروني أو كلمة السر غير صحيحة"
        except Exception as e:
            # طباعة الخطأ في الـ Logs
            print(f"CRITICAL ERROR: {str(e)}")
            return f"حدث خطأ داخلي في قاعدة البيانات: {str(e)}"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/products', methods=['GET', 'POST'])
def products():
    if 'company_id' not in session: return redirect(url_for('login'))
    
    company_id = session['company_id']
    if request.method == 'POST':
        data = {
            "company_id": int(company_id),
            "name": request.form.get('name'),
            "quantity": int(request.form.get('quantity') or 0),
            "price": float(request.form.get('price') or 0.0)
        }
        try:
            supabase.table("inventory").insert(data).execute()
        except Exception as e:
            print(f"PRODUCT INSERT ERROR: {str(e)}")
        return redirect(url_for('products'))
    
    res =
