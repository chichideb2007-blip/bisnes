from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
# تأكدي أن هذا المفتاح موجود
app.secret_key = 'super_secret_key_change_me' 

# التأكد من تحميل المتغيرات بشكل صحيح
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

# منع حدوث خطأ إذا كانت المتغيرات غير موجودة في Render
if not url or not key:
    print("خطأ: يرجى التأكد من إضافة SUPABASE_URL و SUPABASE_KEY في إعدادات Render")
    supabase = None
else:
    supabase = create_client(url, key)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not supabase: return "خطأ في اتصال قاعدة البيانات"
        
        user = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
        
        if user.data:
            session['company_id'] = user.data[0]['company_id']
            return redirect(url_for('dashboard'))
        else:
            return "بيانات الدخول خاطئة"
            
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/settings')
def settings():
    if 'company_id' not in session:
        return redirect(url_for('login'))
    return render_template('settings.html')

if __name__ == '__main__':
    app.run(debug=True)
