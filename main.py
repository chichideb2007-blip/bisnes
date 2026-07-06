from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
# في الإنتاج، يجب أن يكون هذا المفتاح طويلاً وعشوائياً جداً
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-key-for-production")

# نستخدم المتغيرات من النظام (Render) وليس الكود
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- دالة مساعدة للتحقق من تسجيل الدخول ---
def is_logged_in():
    return 'user_id' in session

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # في مشروع تجاري: هنا نتحقق من اسم المستخدم وكلمة المرور من قاعدة البيانات
        # إذا تم التحقق بنجاح:
        session['user_id'] = "company_123"  # مثال: ID الشركة
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if not is_logged_in(): return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if not is_logged_in(): return redirect(url_for('login'))
    
    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('total_price', 0)),
            "customer_phone": request.form.get('customer_phone'),
            "company_id": session['user_id'] # ربط الطلبية بالشركة
        }
        supabase.table('orders').insert(data).execute()
        return redirect(url_for('orders'))
    
    # جلب البيانات الخاصة بهذه الشركة فقط
    response = supabase.table('orders').select('*').eq('company_id', session['user_id']).execute()
    return render_template('users.html', orders=response.data)

@app.route('/delete_order/<int:order_id>', methods=['POST']) # استخدمنا POST للأمان
def delete_order(order_id):
    if not is_logged_in(): return redirect(url_for('login'))
    
    # الحذف مشروط بـ company_id لضمان عدم حذف طلبية شركة أخرى
    supabase.table('orders').delete().eq('id', order_id).eq('company_id', session['user_id']).execute()
    return redirect(url_for('orders'))

# ... (باقي الدوال بنفس نمط التحقق)
