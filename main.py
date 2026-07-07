import os
from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        # استخدام أسماء الأعمدة الفعلية التي رأيتها في جدول orders
        data = {
            "customer_name": request.form.get("customer_name"),
            "customer_phone": request.form.get("customer_phone"),
            "product_name": request.form.get("product_name"),
            "total_price": float(request.form.get("total_price", 0)),
            "status": "قيد الانتظار" 
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    # جلب الطلبات
    response = supabase.table("orders").select("*").execute()
    return render_template('orders_dashboard.html', orders=response.data)

@app.route('/products', methods=['GET', 'POST'])
def products():
    if request.method == 'POST':
        # استخدام أسماء الأعمدة الفعلية في جدول products
        data = {
            "name": request.form.get("name"),
            "price": float(request.form.get("price", 0)),
            "quantity": int(request.form.get("quantity", 0))
        }
        supabase.table("products").insert(data).execute()
        return redirect(url_for('products'))
    
    response = supabase.table("products").select("*").execute()
    return render_template('products.html', products=response.data)

if __name__ == '__main__':
    app.run(debug=True)
