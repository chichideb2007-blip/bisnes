import os
from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client

# تعريف التطبيق وتحديد مجلد القوالب
app = Flask(__name__, template_folder='templates')
app.secret_key = 'chaima_secure_2026'

# إعداد الاتصال بـ Supabase من متغيرات البيئة في Render
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # استعلام التحقق من البيانات
        response = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
        
        if response.data:
            session['user'] = username
            return redirect(url_for('dashboard'))
            
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('users.html')

if __name__ == '__main__':
    # استخدام المنفذ الذي تحدده Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
