from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = "shimo-secure-2026"

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user_id'] = "manager_shimo_id"
        return redirect(url_for('orders'))
    return render_template('login.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        # حفظ الطلب الجديد
        data = {
            "customer_name": request.form.get('customer_name'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('total_price', 0))
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    # جلب الطلبات
    res = supabase.table("orders").select("*").execute()
    return render_template('users.html', orders=res.data)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
