import os
from flask import Flask, render_template, request, redirect, session
from flask_mail import Mail, Message
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'chaima_pro_2026'

# --- إعدادات الإيميل ---
# نصيحة: في Render، ضعي هذه القيم في Environment Variables
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com' # إيميلك الخاص بالإرسال
app.config['MAIL_PASSWORD'] = 'your-app-password'     # كلمة مرور التطبيق من Google

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
            user = response.data[0]
            session['user'] = username
            session['email'] = user.get('email') # تخزين إيميل المدير في الجلسة
            return redirect('/dashboard')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        
        # حفظ المدير الجديد مع إيميله
        supabase.table("users").insert({
            "username": username, 
            "password": password, 
            "email": email
        }).execute()
        
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
    
    # إضافة الطلب
    data = {"customer_name": c_name, "product_name": p_name, "total_price": price, "manager_id": session['user']}
    supabase.table("orders").insert(data).execute()
    
    # إرسال الإيميل للمدير (الإيميل مخزن في الـ session عند تسجيل الدخول)
    manager_email = session.get('email')
    if manager_email:
        send_order_email(manager_email, f"الزبون: {c_name} | المنتج: {p_name} | السعر: {price}")
    
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
