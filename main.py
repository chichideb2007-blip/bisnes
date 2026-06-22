import os
from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'chaima_secret_2026'

# تأكدي من أن هذه المتغيرات موجودة في Render -> Environment
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        response = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
        if response.data:
            session['user'] = username
            return redirect('/dashboard')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    # جلب البيانات
    orders = supabase.table("orders").select("*").execute()
    total = sum(int(item['total_price']) for item in orders.data)

    return render_template('users.html', orders=orders.data, total=total)

@app.route('/add', methods=['POST'])
def add():
    name = request.form.get('product_name')
    price = request.form.get('price')
    supabase.table("orders").insert({"product_name": name, "price": price}).execute()
    return redirect('/dashboard')

@app.route('/delete/<int:id>')
def delete(id):
    supabase.table("orders").delete().eq("id", id).execute()
    return redirect('/dashboard')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
