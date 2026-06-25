from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = "shimo-secure-2026"

# الاتصال بـ Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # في حالتك الحالية، هذا هو المعرف الذي تستخدمينه
        session['user_id'] = "manager_shimo_id" 
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    # التأكد من وجود جلسة دخول
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    
    # جلب الطلبات (تأكدي من أن اسم العمود في جدولك هو user_id تماماً)
    res = supabase.table("orders").select("*").eq("user_id", user_id).execute()
    orders = res.data if res.data is not None else []
    
    return render_template('dashboard.html', orders=orders)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
