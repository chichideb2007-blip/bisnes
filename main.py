from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default-secret-key')

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # تعيين جلسة ثابتة كما في كودك الأصلي
        session['user_id'] = 'aeebc99-9c0b-4efb-8b6d-8bb9bd88a11'
        return redirect(url_for('orders'))
    return render_template('login.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('total_price', 0)),
            "customer_phone": request.form.get('customer_phone'),
            "company_id": user_id
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    # جلب البيانات
    response = supabase.table("orders").select("*").eq("company_id", user_id).execute()
    return render_template('orders_dashboard.html', orders=response.data)

@app.route('/delete_order/<order_id>')
def delete_order(order_id):
    supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect(url_for('orders'))

# باقي الدوال (register, stats, settings) تظل كما هي في كودك
if __name__ == '__main__':
    app.run()
