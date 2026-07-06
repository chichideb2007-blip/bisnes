from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-key-123")

supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# 1. المسارات الأساسية
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user_id'] = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11" 
        return redirect(url_for('orders'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')

# 2. مسارات لوحة التحكم
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    company_id = session.get('user_id')
    if not company_id:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('total_price', 0)),
            "customer_phone": request.form.get('customer_phone'),
            "company_id": company_id 
        }
        supabase.table('orders').insert(data).execute()
        return redirect(url_for('orders'))
    
    response = supabase.table('orders').select('*').eq('company_id', company_id).execute()
    return render_template('users.html', orders=response.data)

@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    company_id = session.get('user_id')
    if not company_id:
        return redirect(url_for('login'))
    
    supabase.table('orders').delete().eq('id', order_id).eq('company_id', company_id).execute()
    return redirect(url_for('orders'))

# 3. مسارات إضافية (تمت إضافتها لمنع الخطأ)
@app.route('/stats')
def stats():
    return render_template('stats.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
