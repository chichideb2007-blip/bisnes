import os
from flask import Flask, render_template, request, redirect, session
from flask_mail import Mail, Message
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'chaima_pro_2026'

# --- إعدادات الإيميل ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com' # ضعي إيميلك هنا
app.config['MAIL_PASSWORD'] = 'your-app-password'     # ضعي كلمة مرور التطبيق هنا
mail = Mail(app)

# --- الاتصال بـ Supabase ---
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- دالة إرسال الإيميل ---
def send_order_email(manager_email, order_details):
    try:
        msg = Message("طلب جديد في متجرك!", sender='your-email@gmail.com', recipients=[manager_email])
        msg.body = f"تفاصيل الطلب الجديد:\n{order_details}"
        mail.send(msg)
    except Exception as e:
        print(f"خطأ في إرسال الإيميل: {e}")

# --- المسارات ---

@app.route('/')
def index():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        response = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
        if response.data:
            session['user'] = username
            return redirect('/dashboard')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        supabase.table("users").insert({"username": username, "password": password}).execute()
        return redirect('/login')
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/login')
    response = supabase.table("orders").select("*").eq("manager_id", session['user']).execute()
    orders = response.data
    total = sum(float(item.get('total_price', 0)) for item in orders if item.get('total_price'))
    return render_template('users.html', orders=orders, total=total)

@app.route('/add', methods=['POST'])
def add():
    if 'user' not in session: return redirect('/login')
    
    c_name = request.form.get('customer_name')
    p_name = request.form.get('product_name')
    price = request.form.get('total_price')
    
    data = {"customer_name": c_name, "product_name": p_name, "total_price": price, "manager_id": session['user']}
    supabase.table("orders").insert(data).execute()
    
    # إرسال إيميل للمدير عند إضافة طلب
    # (ملاحظة: استبدلي 'manager@example.com' بإيميل المدير الحقيقي)
    send_order_email('manager@example.com', f"الزبون: {c_name} | المنتج: {p_name} | السعر: {price}")
    
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
