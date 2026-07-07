from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client
import os

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'your_secret_key_here'

# إعداد اتصال Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # مؤقتاً: سنقوم فقط بالتحويل إلى الداشبورد عند الضغط على دخول
        # لاحقاً سنضيف منطق التحقق من اسم المستخدم
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

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
