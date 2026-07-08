from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
from datetime import datetime

app = Flask(__name__)
# يجب أن يكون مفتاحاً سرياً ثابتاً
app.secret_key = 'your_secret_key_here'

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- المسارات الأساسية ---

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
        if user.data:
            session['company_id'] = user.data[0]['company_id']
            return redirect(url_for('dashboard'))
        return "بيانات الدخول خاطئة"
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # هنا يجب أن تضعي كود إضافة المستخدم لقاعدة البيانات
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    # جلب الطلبات
    response = supabase.table("orders").select("*").eq("company_id", comp_id).execute()
    return render_template('orders_dashboard.html', orders=response.data)

@app.route('/stats')
def stats():
    if 'company_id' not in session: return redirect(url_for('login'))
    # هنا يظهر منطق الإحصائيات الذي صممناه
    return render_template('stats.html')

# --- حل مشكلة Not Found (إضافة المسار المفقود) ---
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
