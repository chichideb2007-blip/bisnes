from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client
import os
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

app = Flask(__name__)
app.secret_key = 'shimo_secure_key_2026'

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('total_price', 0)),
            "customer_phone": request.form.get('customer_phone')
        }
        supabase.table('orders').insert(data).execute()
        return redirect(url_for('orders'))
    
    response = supabase.table('orders').select('*').execute()
    return render_template('users.html', orders=response.data)

# --- التعديل الأساسي هنا ---
@app.route('/delete_order/<int:order_id>', methods=['GET'])
def delete_order(order_id):
    try:
        # تنفيذ عملية الحذف في Supabase
        supabase.table('orders').delete().eq('id', order_id).execute()
    except Exception as e:
        print(f'Error deleting: {e}')
    return redirect(url_for('orders'))
# ---------------------------

@app.route('/stats', methods=['GET'])
def stats():
    response = supabase.table('orders').select('total_price').execute()
    total_sales = sum(float(item.get('total_price', 0)) for item in response.data)
    return render_template('stats.html', total_sales=total_sales)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    return render_template('settings.html')

@app.route('/logout')
def logout():
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
