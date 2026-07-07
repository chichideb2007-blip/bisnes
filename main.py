from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client
import os

# تعريف المسارات: تم وضع مجلد static في الخارج ليراه Flask بشكل صحيح
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'your_secret_key'

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- المسارات الأساسية (يجب أن تكون متطابقة مع روابطك في HTML) ---

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/stats')
def stats():
    return render_template('stats.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    try:
        response = supabase.table("orders").select("*").execute()
        orders_data = response.data
    except:
        orders_data = []
    return render_template('orders_dashboard.html', orders=orders_data)

if __name__ == '__main__':
    app.run(debug=True)
