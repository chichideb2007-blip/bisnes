from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        # التحقق من المستخدم في Supabase
        user = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
        if user.data:
            session['company_id'] = user.data[0]['company_id']
            return redirect(url_for('dashboard'))
        return "بيانات الدخول خاطئة"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/settings')
def settings():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('settings.html')

# تأكدي من وجود مسار register أيضاً
@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True)
