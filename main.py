from flask import Flask, render_template, request, redirect, url_for, session
import os
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'shimo_secret_key'

# الاتصال بقاعدة البيانات
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key) if url and key else None

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    # جلب الطلبات
    orders_data = supabase.table("orders").select("*").execute().data if supabase else []
    return render_template('orders_dashboard.html', orders=orders_data)

@app.route('/settings')
def settings():
    return render_template('settings.html')

if __name__ == '__main__':
    app.run(debug=True)
