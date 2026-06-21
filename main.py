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

@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('get_users'))
    return redirect(url_for('login'))
