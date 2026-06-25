from flask import Flask, render_template, request, redirect, session, url_for
import os

app = Flask(__name__)
app.secret_key = "shimo-secure-2026"

# المسار الرئيسي يوجه لصفحة الدخول
@app.route('/')
def home():
    return redirect(url_for('login'))

# مسار صفحة الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # هنا تضعين كود التحقق من قاعدة البيانات لاحقاً
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# مسار لوحة التحكم
@app.route('/dashboard')
def dashboard():
    # في مشروع حقيقي ستحتاجين للتأكد من تسجيل الدخول هنا
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
