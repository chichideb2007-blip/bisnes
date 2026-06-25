from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = "shimo-secure-2026"

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user_id'] = "manager_shimo_id"
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    
    # جلب الطلبات
    res = supabase.table("orders").select("*").eq("user_id", user_id).execute()
    orders = res.data if res.data is not None else []
    
    # جلب الإعدادات (تأكدنا هنا أنها لن تكون فارغة)
    set_res = supabase.table("settings").select("*").eq("user_id", user_id).maybe_single().execute()
    settings = set_res.data if set_res.data is not None else {"shop_name": "متجري", "primary_color": "#7e22ce"}
    
    return render_template('dashboard.html', orders=orders, settings=settings)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
