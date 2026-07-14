from flask import Flask, render_template, request, redirect, url_for, session
import os

# تعريف التطبيق مع تحديد مجلد القوالب
app = Flask(__name__, template_folder='templates')
# تأكدي من ضبط SECRET_KEY في إعدادات البيئة في Render
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

# مسار الصفحة الرئيسية
@app.route('/')
def home():
    return "الموقع يعمل بنجاح! - <a href='/login'>اذهب لصفحة الدخول</a>"

# مسار تسجيل الدخول المدمج (يستقبل GET و POST)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # هنا يتم معالجة البيانات المرسلة من النموذج
        email = request.form.get('email')
        password = request.form.get('password')
        
        # مثال للتحقق (استبدليه بمنطق Supabase لاحقاً)
        if email and password:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        
        return "بيانات الدخول غير مكتملة"
    
    # في حالة GET، نعرض صفحة login.html
    return render_template('login.html')

# مسار لوحة التحكم
@app.route('/dashboard')
def dashboard():
    return "مرحباً بكِ في لوحة التحكم!"

if __name__ == '__main__':
    app.run()
