from flask import Flask, request, render_template, session, redirect, url_for
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = 'shimo_secret_key_2026'

# إعداد Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('get_users'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
        
        if user.data:
            session['user'] = username
            return redirect(url_for('get_users'))
        else:
            return "بيانات الدخول خاطئة!"
    return render_template('login.html')

@app.route('/users')
def get_users():
    if 'user' not in session:
        return redirect(url_for('login'))
    response = supabase.table("users").select("*").execute()

    return render_template('users.html', users=response.data)

@app.route('/add_user', methods=['POST'])
def add_user():
    name = request.form.get('customer_name')
    if name:
        supabase.table("users_data").insert({"customer_name": name}).execute()
    return redirect(url_for('get_users'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
