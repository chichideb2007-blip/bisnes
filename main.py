from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "shimo_2026_key"

# المسار الرئيسي - تحويل تلقائي لصفحة تسجيل الدخول
@app.route('/')
def home():
    return redirect(url_for('login'))

# صفحة تسجيل الدخول
@app.route('/login')
def login():
    return render_template('login.html')

# لوحة التحكم الرئيسية
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# صفحة الطلبيات
@app.route('/orders')
def orders():
    return render_template('orders.html')

# صفحة الإحصائيات
@app.route('/stats')
def stats():
    return render_template('stats.html')

# صفحة الإعدادات
@app.route('/settings')
def settings():
    return render_template('settings.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
