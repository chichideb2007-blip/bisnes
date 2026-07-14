from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from google import genai
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.before_request
def check_session():
    # السماح بالوصول لهذه الصفحات بدون تسجيل دخول
    if request.endpoint in ['login', 'register', 'static']: return
    if 'company_id' not in session: return redirect(url_for('login'))

# 1. المخزن (Inventory)
@app.route('/products', methods=['GET', 'POST'])
def products():
    if request.method == 'POST':
        # التأكد من وجود البيانات وتجنب null في company_id
        company_id = session.get('company_id')
        if company_id:
            supabase.table("inventory").insert({
                "company_id": company_id,
                "name": request.form.get('name'),
                "quantity": int(request.form.get('quantity') or 0),
                "price": float(request.form.get('price') or 0)
            }).execute()
        return redirect(url_for('products'))
    
    res = supabase.table("inventory").select("*").eq("company_id", session['company_id']).execute()
    return render_template('products.html', products=res.data or [])

# 2. الطلبيات (Orders)
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        supabase.table("orders").insert({
            "company_id": session['company_id'],
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('customer_phone'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('total_price') or 0),
            "status": "قيد الانتظار"
        }).execute()
        return redirect(url_for('orders'))
    
    res = supabase.table("orders").select("*").eq("company_id", session['company_id']).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

# 3. الإحصائيات (Stats)
@app.route('/stats')
def stats():
    res = supabase.table("orders").select("*").eq("company_id", session['company_id']).execute()
    return render_template('stats.html', orders=res.data or [])

# 4. الإعدادات (Settings)
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        supabase.table("companies").update({
            "store_name": request.form.get('store_name'),
            "telegram_token": request.form.get('token'),
            "manager_phone": request.form.get('phone')
        }).eq("id", session['company_id']).execute()
        return redirect(url_for('settings'))
    
    res = supabase.table("companies").select("*").eq("id", session['company_id']).execute()
    settings_data = res.data[0] if res.data else {}
    return render_template('settings.html', settings=settings_data)

# 5. تسجيل الخروج
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
