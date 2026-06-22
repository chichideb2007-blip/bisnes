from flask import Flask, request, render_template, session, redirect, url_for
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = 'shimo_secret_key_2026'

supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# المسار الرئيسي يوجهك للشركات مباشرة
@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('get_data', table_name='companies'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
        if user.data:
            session['user'] = username
            return redirect(url_for('get_data', table_name='companies'))
    return render_template('login.html')

# دالة ذكية تجلب البيانات من أي جدول تختارينه
@app.route('/view/<table_name>')
def get_data(table_name):
    if 'user' not in session:
        return redirect(url_for('login'))
    # جلب البيانات
    response = supabase.table(table_name).select("*").execute()
    return render_template('users.html', data=response.data, table=table_name)

# دالة ذكية تضيف البيانات لأي جدول
@app.route('/add/<table_name>', methods=['POST'])
def add_data(table_name):
    name = request.form.get('name')
    if name:
        supabase.table(table_name).insert({"name": name}).execute()
    return redirect(url_for('get_data', table_name=table_name))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
