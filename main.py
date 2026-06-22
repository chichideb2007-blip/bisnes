import os
from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'chaima_secret_key_2026'

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
        if user.data:
            session['user'] = username
            return "تم تسجيل الدخول بنجاح"
    return render_template('login.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
