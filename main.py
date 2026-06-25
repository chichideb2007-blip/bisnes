from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = "shimo-secure-2026"

# الاتصال بـ Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # في حالتك هذه، هذا هو المعرف الذي تستخدمينه
        session['user_id'] = "manager_shimo_id"
        return redirect(url_for('orders'))
    return render_template('login.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']

    if request.method == 'POST':
        # إضافة طلب جديد مع مطابقة أسماء الأعمدة في Supabase
        data = {
            "customer_name": request.form.get('customer_name'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('total_price', 0)),
            "customer_phone": request.form.get('customer_phone'),
            "user_id": user_id
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    # جلب الطلبات الخاصة بالمستخدم فقط
    res = supabase.table("orders").select("*").eq("user_id", user_id).execute()
    orders_list = res.data if res.data is not None else []
    
    return render_template('orders_dashboard.html', orders=orders_list)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
