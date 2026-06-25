from flask import Flask, render_template, redirect, url_for
import os

app = Flask(__name__)

# هذا المسار يحل مشكلة الـ 404
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

if __name__ == '__main__':
    # Render يستخدم المتغير PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
