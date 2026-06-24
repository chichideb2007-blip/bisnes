import os
from flask import Flask, render_template, request, session, redirect
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'shimo_clean_start_2026'

# تأكدي من إعدادات الـ Environment في Render
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key) if url and key else None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    session['user'] = request.form.get('username')
    return redirect('/dashboard')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    return render_template('dashboard.html', user=session['user'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
