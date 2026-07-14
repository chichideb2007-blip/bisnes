from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

# تعريف التطبيق مع تحديد مجلد القوالب
app = Flask(__name__, template_folder='templates')
# تأكدي من ضبط SECRET_KEY في إعدادات البيئة في Render
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

# إعداد Supabase باستخدام متغيرات البيئة
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# 1. مسار الصفحة الرئيسية
@app.route('/')
def home():
    return "الموقع يعمل بنجاح! - <a href='/login'>اذهب لصفحة الدخول</a>"

# 2. مسار تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # الاتصال بقاعدة البيانات والتحقق من المستخدم
        res = supabase.table("companies").select("*").eq("email", email).execute()

        if res.data and res.data[0]['password'] == password:
            session['company_id'] = res.data[0]['id']
            return redirect(url_for('dashboard'))

        return "بيانات الدخول خاطئة"
    return render_template('login.html')

# 3. مسار لوحة التحكم
@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# 4. مسارات الأقسام الجديدة
@app.route('/orders')
def orders():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('orders.html')

@app.route('/statistics')
def statistics():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('statistics.html')

@app.route('/inventory')
def inventory():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('inventory.html')

@app.route('/settings')
def settings():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('settings.html')

# 5. تسجيل الخروج
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run()
