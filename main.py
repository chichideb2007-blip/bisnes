from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

# تعريف التطبيق مع تحديد مجلد القوالب
app = Flask(__name__, template_folder='templates')
# تأكدي من ضبط SECRET_KEY في إعدادات البيئة في Render
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

# إعداد Supabase باستخدام متغيرات البيئة
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# مسار الصفحة الرئيسية
@app.route('/')
def home():
    return "الموقع يعمل بنجاح! - <a href='/login'>اذهب لصفحة الدخول</a>"

# مسار تسجيل الدخول المدمج (يستقبل GET و POST مع Supabase)
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

# مسار لوحة التحكم
@app.route('/dashboard')
def dashboard():
    # التحقق من أن المستخدم مسجل الدخول
    if 'company_id' not in session:
        return redirect(url_for('login'))
    return "مرحباً بكِ في لوحة التحكم!"

if __name__ == '__main__':
    app.run()
