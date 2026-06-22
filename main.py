from flask import Flask, request, render_template, session, redirect, url_for
from supabase import create_client
import os

app = Flask(__name__)
# مفتاح الجلسة لضمان أمان الموقع
app.secret_key = 'shimo_secret_key_2026'

# إعداد اتصال سوبابايس (تأكدي أن المتغيرات موجودة في إعدادات Render)
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # جلب بيانات المستخدم من الجدول
        user = supabase.table("users").select("*").eq("username", username).execute()
        
        # التحقق من وجود المستخدم ومطابقة كلمة المرور
        if user.data and len(user.data) > 0:
            if user.data[0].get('password') == password:
                session.clear()
                session['user'] = username
                # حفظ الـ company_id في الجلسة لاستخدامه لاحقاً
                session['company_id'] = user.data[0].get('company_id') or 0
                return redirect(url_for('get_data'))
        return "بيانات الدخول خاطئة!"
    return render_template('login.html')

@app.route('/data')
def get_data():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    comp_id = session.get('company_id', 0)
    
    # جلب الطلبات الخاصة بهذه الشركة فقط
    response = supabase.table("orders").select("*").eq("company_id", comp_id).execute()
    return render_template('users.html', users=response.data)

@app.route('/add_data', methods=['POST'])
def add_data():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    order_name = request.form.get('order_name')
    comp_id = session.get('company_id', 0)
    
    if order_name:
        try:
            supabase.table("orders").insert({
                "order_name": order_name, 
                "company_id": int(comp_id)
            }).execute()
        except Exception as e:
            return f"حدث خطأ أثناء الإضافة: {str(e)}"
        
    return redirect(url_for('get_data'))
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
