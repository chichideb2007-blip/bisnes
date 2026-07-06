from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
# تأكدي من ضبط FLASK_SECRET_KEY في إعدادات Render (قسم Environment)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-key-123")

# إعداد Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# 1. الصفحة الرئيسية - توجيه تلقائي لتسجيل الدخول
@app.route('/')
def home():
    return redirect(url_for('login'))

# 2. صفحة تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # في مشروعك الحقيقي، تحقق من البريد وكلمة السر هنا
        # حالياً نضع ID تجريبي لعمل الجلسة
        session['user_id'] = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11" 
        return redirect(url_for('orders'))
    return render_template('login.html')

# 3. صفحة الطلبيات - عرض وإضافة
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
            "company_id": company_id 
        }
        supabase.table('orders').insert(data).execute()
        return redirect(url_for('orders'))
    
    # جلب البيانات الخاصة بهذه الشركة فقط
    response = supabase.table('orders').select('*').eq('company_id', company_id).execute()
    return render_template('users.html', orders=response.data)

# 4. دالة الحذف
@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    company_id = session.get('user_id')
    if not company_id:
        return redirect(url_for('login'))
    
    supabase.table('orders').delete().eq('id', order_id).eq('company_id', company_id).execute()
    return redirect(url_for('orders'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
