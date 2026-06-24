import os
from flask import Flask, render_template, request, session, redirect
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'shimo_settings_pro_2026'

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key) if url and key else None

@app.route('/')
def index(): 
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user'] = request.form.get('username')
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/dashboard', methods=['GET'])
def dashboard():
    if 'user' not in session: 
        return redirect('/login')
    orders = []
    settings = {"shop_name": "متجري الإلكتروني", "telegram_bot_token": "", "telegram_chat_id": "", "primary_color": "#1e3c72", "secondary_color": "#2a5298"}
    
    if supabase:
        try:
            # جلب الطلبات
            response_orders = supabase.table("orders").select("*").execute()
            orders = response_orders.data if response_orders.data else []
            
            # جلب الإعدادات (السطر رقم 1)
            response_settings = supabase.table("settings").select("*").eq("id", 1).execute()
            if response_settings.data:
                settings = response_settings.data[0]
        except Exception as e: 
            print(f"Error fetching data: {e}")
            
    return render_template('dashboard.html', user=session['user'], orders=orders, settings=settings)

@app.route('/add-order', methods=['POST'])
def add_order():
    if 'user' not in session: 
        return redirect('/login')
    if supabase:
        try:
            supabase.table("orders").insert({
                "customer_name": request.form.get('name'),
                "product_name": request.form.get('product'),
                "total_price": float(request.form.get('price', 0)) if request.form.get('price') else 0.0,
                "customer_phone": request.form.get('phone')
            }).execute()
        except Exception as e: 
            print(f"Error adding order: {e}")
    return redirect('/dashboard')

@app.route('/delete-order', methods=['POST'])
def delete_order():
    if 'user' not in session: 
        return redirect('/login')
    order_id = request.form.get('order_id')
    if supabase and order_id:
        try:
            supabase.table("orders").delete().eq("id", order_id).execute()
        except Exception as e: 
            print(f"Error deleting: {e}")
    return redirect('/dashboard')

@app.route('/edit-order', methods=['POST'])
def edit_order():
    if 'user' not in session: 
        return redirect('/login')
    order_id = request.form.get('order_id')
    if supabase and order_id:
        try:
            supabase.table("orders").update({
                "customer_name": request.form.get('name'),
                "product_name": request.form.get('product'),
                "total_price": float(request.form.get('price', 0)) if request.form.get('price') else 0.0,
                "customer_phone": request.form.get('phone')
            }).eq("id", order_id).execute()
        except Exception as e: 
            print(f"Error editing: {e}")
    return redirect('/dashboard')

@app.route('/update-settings', methods=['POST'])
def update_settings():
    if 'user' not in session: 
        return redirect('/login')
    if supabase:
        try:
            # تحديث الإعدادات في قاعدة البيانات
            supabase.table("settings").update({
                "shop_name": request.form.get('shop_name'),
                "telegram_bot_token": request.form.get('bot_token'),
                "telegram_chat_id": request.form.get('chat_id'),
                "primary_color": request.form.get('primary_color'),
                "secondary_color": request.form.get('secondary_color')
            }).eq("id", 1).execute()
        except Exception as e:
            print(f"Error updating settings: {e}")
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
