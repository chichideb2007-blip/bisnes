from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = 'shimo_secret_key_2026'

supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None 
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = supabase.table("users").select("*").eq("username", username).execute()
        if user.data and len(user.data) > 0 and user.data[0].get('password') == password:
            session['user'] = username
            session['company_id'] = user.data[0].get('company_id')
            return redirect(url_for('get_data'))
        else:
            error = "اسم المستخدم أو كلمة السر غير صحيحة!"
    return render_template('login.html', error=error)

@app.route('/data')
def get_data():
    if 'user' not in session: return redirect(url_for('login'))
    comp_id = session.get('company_id', 0)
    response = supabase.table("orders").select("*").eq("company_id", comp_id).execute()
    return render_template('users.html', users=response.data)

@app.route('/add_data', methods=['POST'])
def add_data():
    if 'user' not in session: return "Unauthorized", 401
    order_name = request.form.get('order_name')
    comp_id = session.get('company_id', 0)
    if order_name:
        try:
            supabase.table("orders").insert({"order_name": order_name, "company_id": int(comp_id)}).execute()
            return "Success", 200
        except Exception as e:
            return str(e), 500
    return "No Data", 400

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
