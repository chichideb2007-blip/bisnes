 import os
from flask import Flask, render_template, request, redirect
from supabase import create_client

app = Flask(__name__)
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key) if url and key else None

def get_settings():
    default = {"shop_name": "متجري", "primary_color": "#7a3e13", "secondary_color": "#bd6a2c"}
    if not supabase: return default
    res = supabase.table("settings").select("*").eq("id", 1).execute()
    return res.data[0] if res.data else default

@app.route('/')
def dashboard():
    orders = supabase.table("orders").select("*").execute().data if supabase else []
    return render_template('dashboard.html', orders=orders, settings=get_settings())

@app.route('/add-order', methods=['POST'])
def add_order():
    if supabase:
        supabase.table("orders").insert({
            "customer_name": request.form.get('name'), 
            "product_name": request.form.get('product'), 
            "total_price": float(request.form.get('price', 0)), 
            "customer_phone": request.form.get('phone')
        }).execute()
    return redirect('/')

@app.route('/delete-order', methods=['POST'])
def delete_order():
    if supabase: supabase.table("orders").delete().eq("id", request.form.get('order_id')).execute()
    return redirect('/')

@app.route('/update-info', methods=['POST'])
def update_info():
    if supabase:
        supabase.table("settings").update({
            "shop_name": request.form.get('shop_name'),
            "telegram_bot_token": request.form.get('bot_token'),
            "telegram_chat_id": request.form.get('chat_id')
        }).eq("id", 1).execute()
    return redirect('/')

@app.route('/update-colors', methods=['POST'])
def update_colors():
    if supabase:
        supabase.table("settings").update({
            "primary_color": request.form.get('primary_color'),
            "secondary_color": request.form.get('secondary_color')
        }).eq("id", 1).execute()
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
