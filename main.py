from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
# مفتاح سري لتشفير الجلسات (مهم جداً لكي لا يخرجكِ النظام)
app.secret_key = 'your_super_secret_key' 

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# 1. صفحة الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # التحقق من المستخدم
        user = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
        
        if user.data:
            # حفظ ID الشركة في الجلسة لعزل البيانات
            session['company_id'] = user.data[0]['company_id']
            return redirect(url_for('dashboard'))
        else:
            return "بيانات الدخول خاطئة"
            
    return render_template('login.html')

# 2. لوحة التحكم (محمية بالجلسة)
@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# 3. تسجيل حساب جديد
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # أضيفي هنا منطق إضافة المستخدم لقاعدة البيانات
        return redirect(url_for('login'))
    return render_template('register.html')

# 4. صفحة الإعدادات (لمنع خطأ 404)
@app.route('/settings')
def settings():
    if 'company_id' not in session:
        return redirect(url_for('login'))
    return render_template('settings.html')

if __name__ == '__main__':
    app.run(debug=True)
