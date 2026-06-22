import os
from flask import Flask, render_template, request, redirect, session
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'chaima_secret_2026'

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    orders = supabase.table("orders").select("*").execute()
    
    # هذه الطريقة ستمنع ظهور خطأ KeyError تماماً
    processed_orders = []
    total = 0
    for item in orders.data:
        # يحاول البحث عن total_price أولاً، ثم price
        price_val = item.get('total_price') or item.get('price') or 0
        item['price_display'] = price_val
        total += float(price_val)
        processed_orders.append(item)
        
    return render_template('users.html', orders=processed_orders, total=total)

@app.route('/add', methods=['POST'])
def add():
    name = request.form.get('product_name')
    price = request.form.get('total_price')
    # نحاول الإدخال باسم total_price
    supabase.table("orders").insert({"product_name": name, "total_price": price}).execute()
    return redirect('/dashboard')
# ... (باقي الدوال كما هي)
