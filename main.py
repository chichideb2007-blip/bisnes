from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client
import os

app = Flask(__name__)

# الاتصال بـ Supabase (تأكدي من وجودها في Environment Variables في Render)
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/')
def home():
    # جلب البيانات مباشرة للتأكد من الاتصال
    try:
        res = supabase.table("orders").select("*").execute()
        orders = res.data if res.data else []
    except Exception as e:
        orders = []
        print(f"Error: {e}")
        
    return render_template('dashboard.html', orders=orders)

@app.route('/add-order', methods=['POST'])
def add_order():
    data = {
        "customer_name": request.form.get('name'),
        "product_name": request.form.get('product'),
        "total_price": float(request.form.get('price', 0)),
        "customer_phone": request.form.get('phone')
    }
    supabase.table("orders").insert(data).execute()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
