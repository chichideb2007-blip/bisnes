from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
# تأكدي من ضبط FLASK_SECRET_KEY في إعدادات Environment في موقع Render
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your-secret-key-here")

# إعداد Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# 1. المسار الجذري
@app.route('/')
def home():
    return redirect(url_for('login'))

# 2. صفحة تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # مستقبلاً سنضيف التحقق من قاعدة البيانات هنا
        session['user_id'] = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11" 
        return redirect(url_for('orders'))
    return render_template('login.html')

# 3. صفحة الطلبيات (العرض والإضافة)
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    company_id = session.get('user_id')
    if not company_id:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('total_price', 0)),
            "customer_phone": request.form.get('customer_phone'),
            "company_id": str(company_id) 
        }
        supabase.table('orders').insert(data).execute()
        return redirect(url_for('orders'))
    
    # استخدام filter بدلاً من eq لحل مشكلة الخطأ في الـ Logs
    response = supabase.table('orders').select('*').filter('company_id', 'eq', str(company_id)).execute()
    return render_template('users.html', orders=response.data)

# 4. دالة الحذف
@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    company_id = session.get('user_id')
    if not company_id:
        return redirect(url_for('login'))
    
    supabase.table('orders').delete().filter('id', 'eq', order_id).filter('company_id', 'eq', str(company_id)).execute()
    return redirect(url_for('orders'))

# 5. صفحات إضافية لمنع أخطاء الـ 404
@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/stats')
def stats():
    return render_template('stats.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
