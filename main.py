from flask import Flask, request, render_template, session, redirect, url_for
from supabase import create_client
import os

app = Flask(__name__)
# هذا المفتاح ضروري لتأمين الجلسات (يمكنك تغيير الكلمة لأي شيء)
app.secret_key = 'shimo_secret_key_2026'

# إعداد Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # التحقق من المستخدم في Supabase
        user = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
        
        if user.data:
            session['user'] = username
            return redirect(url_for('get_users'))
        else:
            return "بيانات الدخول خاطئة!"
            
    return render_template('login.html')

@app.route('/users')
def get_users():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    response = supabase.table("users").select("*").execute()
    return render_template('users.html', users=response.data)

# الجزء الأخير لتشغيل السيرفر
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
