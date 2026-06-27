from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = "shimo-secure-2026"

# إعداد Supabase
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key)

# --- المسارات ---

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # أضيفي منطق التحقق هنا لاحقاً
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# الحل هنا: أضفنا مسار 'register' لمنع الخطأ
@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html') # تأكدي أن ملف register.html موجود في مجلد templates

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    # جلب الطلبات من Supabase
    res = supabase.table("orders").select("*").execute()
    return render_template('orders_dashboard.html', orders=res.data)

@app.route('/stats')
def stats():
    return render_template('stats.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    return render_template('settings.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
