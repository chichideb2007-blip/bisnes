import os
from flask import Flask, render_template, request, redirect, session
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'chaima_pro_2026'

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# هذا الجزء يحل مشكلة الـ 404
@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # كود التحقق من الدخول...
        pass
    return render_template('login.html')

# ... باقي الكود الخاص بـ dashboard و add و delete
