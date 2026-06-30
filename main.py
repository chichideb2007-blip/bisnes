from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = "shimo_secure_key_2026"

# إعداد Supabase (تأكدي أن الروابط موضوعة في إعدادات Render كـ Environment Variables)
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# هذه المسارات سنقوم بتطويرها في الخطوات القادمة
@app.route('/orders')
def orders():
    return render_template('orders_dashboard.html')

@app.route('/stats')
def stats():
    return render_template('stats.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
