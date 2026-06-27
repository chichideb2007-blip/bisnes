from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# المسارات الأساسية
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/orders')
def orders():
    return render_template('orders.html')

@app.route('/stats')
def stats():
    return render_template('stats.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    return render_template('settings.html')

@app.route('/register')
def register():
    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True)
