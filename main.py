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
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# إضافة مسار التسجيل الذي كان يسبب الخطأ
@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    # جلب البيانات من Supabase
    try:
        res = supabase.table("orders").select("*").execute()
        return render_template('orders_dashboard.html', orders=res.data)
    except Exception as e:
        return f"خطأ: {str(e)}"

@app.route('/stats')
def stats():
    return render_template('stats.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    return render_template('settings.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
