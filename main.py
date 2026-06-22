from flask import Flask, request, render_template, session, redirect, url_for
from supabase import create_client
import os

app = Flask(__name__)
# مفتاح الجلسة لضمان أمان العمل
app.secret_key = 'shimo_secret_key_2026'

# إعداد الاتصال بـ Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # جلب المستخدم والتحقق
        user = supabase.table("users").select("username, company_id").eq("username", username).eq("password", password).execute()
        
        if user.data and len(user.data) > 0:
            session.clear() # مسح أي جلسة قديمة
            session['user'] = username
            session['company_id'] = user.data[0]['company_id']
            return redirect(url_for('get_data'))
        return "بيانات الدخول خاطئة!"
    return render_template('login.html')

@app.route('/data')
def get_data():
    if 'company_id' not in session:
        return redirect(url_for('login'))
    
    comp_id = session.get('company_id')
    
    # جلب الطلبات مع تحويل comp_id إلى رقم صحيح
    try:
        response = supabase.table("orders").select("*").eq("company_id", int(comp_id)).execute()
        return render_template('users.html', users=response.data)
    except Exception as e:
        return f"حدث خطأ أثناء جلب البيانات: {str(e)}"

@app.route('/add_data', methods=['POST'])
def add_data():
    if 'company_id' not in session:
        return redirect(url_for('login'))
    
    order_name = request.form.get('order_name')
    comp_id = session.get('company_id')
    
    if order_name:
        try:
            supabase.table("orders").insert({
                "order_name": order_name, 
                "company_id": int(comp_id)
            }).execute()
        except Exception as e:
            return f"خطأ في إضافة البيانات: {str(e)}"
        
    return redirect(url_for('get_data'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
