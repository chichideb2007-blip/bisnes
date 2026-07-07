import os
from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'secret_key_123'

# إعداد الاتصال بـ Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# --- عمليات الطلبيات ---

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        # جلب البيانات من النموذج
        data = {
            "customer_name": request.form.get("customer_name"),
            "customer_phone": request.form.get("customer_phone"),
            "product_name": request.form.get("product_name"),
            "total_price": float(request.form.get("total_price", 0)),
            "status": "قيد الانتظار"
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    # جلب البيانات من الجدول
    response = supabase.table("orders").select("*").execute()
    return render_template('orders_dashboard.html', orders=response.data)

@app.route('/delete_order/<int:order_id>')
def delete_order(order_id):
    supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect(url_for('orders'))

@app.route('/update_order/<int:order_id>')
def update_order(order_id):
    supabase.table("orders").update({"status": "تمت"}).eq("id", order_id).execute()
    return redirect(url_for('orders'))

# --- الصفحات الأخرى ---

@app.route('/stats')
def stats():
    return render_template('stats.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

if __name__ == '__main__':
    app.run(debug=True)
