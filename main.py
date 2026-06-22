from flask import Flask, request, render_template, session, redirect, url_for
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = 'shimo_secret_key_2026'

supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('get_data'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # التحقق من المستخدم
        user = supabase.table("users").select("username, company_id").eq("username", username).eq("password", password).execute()
        if user.data:
            session['user'] = username
            session['company_id'] = user.data[0]['company_id']
            return redirect(url_for('get_data'))
        return "بيانات الدخول خاطئة!"
    return render_template('login.html')

@app.route('/data')
def get_data():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # جلب البيانات الخاصة بهذه الشركة فقط
    comp_id = session.get('company_id')
    response = supabase.table("orders").select("*").eq("company_id", comp_id).execute()
    
    return render_template('users.html', users=response.data)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
