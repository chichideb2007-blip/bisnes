from flask import Flask, request, render_template, session, redirect, url_for
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
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = supabase.table("users").select("username, company_id").eq("username", username).eq("password", password).execute()
        
        # التأكد من وجود مستخدم وأن company_id ليس فارغاً
        if user.data and len(user.data) > 0 and user.data[0].get('company_id') is not None:
            session.clear()
            session['user'] = username
            session['company_id'] = user.data[0]['company_id']
            return redirect(url_for('data'))
        return "بيانات الدخول خاطئة، أو أن حسابك لا يملك معرف شركة (company_id)!"
    return render_template('login.html')

@app.route('/data')
def data():
    comp_id = session.get('company_id')
    if not comp_id:
        return redirect(url_for('login'))
    
    # جلب البيانات مباشرة بدون تحويل معقد
    response = supabase.table("orders").select("*").eq("company_id", comp_id).execute()
    return render_template('users.html', users=response.data)

@app.route('/add_data', methods=['POST'])
def add_data():
    comp_id = session.get('company_id')
    if not comp_id:
        return redirect(url_for('login'))
    
    order_name = request.form.get('order_name')
    if order_name:
        supabase.table("orders").insert({"order_name": order_name, "company_id": comp_id}).execute()
        
    return redirect(url_for('data'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
