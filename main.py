from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = 'secret_key_123'

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/')
def index():
    return "الموقع يعمل بنجاح!"

# --- مسار المخزن (Inventory) ---
# مطابق لأعمدة جدول inventory في سوبابيس (name, quantity, price)
@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if request.method == 'POST':
        # تأكدي أن هذه الأسماء (name, quantity, price) تطابق ما في قاعدة البيانات
        data = {
            "name": request.form.get('name'),
            "quantity": request.form.get('quantity'),
            "price": request.form.get('price'),
            "company_id": "1" # تأكدي من وجود هذا العمود إذا كنتِ تستخدمينه
        }
        supabase.table("inventory").insert(data).execute()
        return redirect(url_for('inventory'))
    
    res = supabase.table("inventory").select("*").execute()
    return render_template('products.html', products=res.data or [])

# --- مسار الطلبات (Orders) ---
# مطابق لأعمدة جدول orders في سوبابيس (customer_name)
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "company_id": "1"
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    res = supabase.table("orders").select("*").execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

if __name__ == '__main__':
    app.run(debug=True)
