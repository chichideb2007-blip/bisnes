import os
from flask import Flask, render_template, request, redirect, session
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'shimo_secret_2026'

# محاولة الاتصال بـ Supabase
try:
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_KEY')
    supabase = create_client(url, key) if url and key else None
except Exception as e:
    supabase = None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # إذا تم تسجيل الدخول، نضع المستخدم في الجلسة
        session['user'] = request.form.get('username')
        return redirect('/dashboard')
    # إذا لم يكن هناك POST، نعرض الصفحة
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    # هنا الحماية إذا لم يكن المستخدم مسجلاً
    if 'user' not in session:
        return redirect('/login')
    
    # محاولة جلب البيانات
    try:
        if supabase:
            orders = supabase.table("orders").select("*").eq("manager_email", session['user']).execute().data
        else:
            orders = []
    except:
        orders = []
        
    return render_template('dashboard.html', orders=orders, total=0)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
