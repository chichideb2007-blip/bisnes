from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here' # تأكدي من تغييره لمفتاح صعب

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- المسارات ---

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            user = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
            if user.data:
                session['company_id'] = user.data[0]['company_id']
                return redirect(url_for('dashboard'))
            return "بيانات الدخول خاطئة"
        except Exception as e:
            return f"خطأ في الاتصال: {e}"
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # أضيفي هنا بيانات الشركة الجديدة
        new_user = {
            "email": request.form.get('email'),
            "password": request.form.get('password'),
            "company_id": request.form.get('company_id') 
        }
        supabase.table("users").insert(new_user).execute()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    try:
        response = supabase.table("orders").select("*").eq("company_id", comp_id).execute()
        orders_list = response.data if response.data else []
    except:
        orders_list = []
    return render_template('orders_dashboard.html', orders=orders_list)

@app.route('/stats')
def stats():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    try:
        response = supabase.table("orders").select("*").eq("company_id", comp_id).execute()
        stats_data = response.data if response.data else []
    except:
        stats_data = []
    return render_template('stats.html', orders=stats_data)

@app.route('/settings')
def settings():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('settings.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
