import os
import requests
from flask import Flask, render_template, request, redirect, session, flash
from supabase import create_client
from datetime import datetime

app = Flask(__name__)
# ضروري لعمل خاصية الـ flash
app.secret_key = 'shimo_secret_key_2026' 

supabase = create_client(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_KEY'))

def get_safe_float(value):
    try: return float(value)
    except: return 0.0

def send_telegram_msg(token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        requests.post(url, data=payload)
    except: pass

@app.route('/')
def home(): return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user'] = request.form.get('username')
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/login')
    s_res = supabase.table("settings").select("*").eq("manager_id", session['user']).maybe_single().execute()
    settings = s_res.data if s_res and s_res.data else {"theme_color": "#4CAF50", "shop_name": "طلباتي"}
    o_res = supabase.table("orders").select("*").eq("manager_id", session['user']).execute()
    orders = o_res.data if o_res and o_res.data else []
    total = sum(get_safe_float(o.get('total_price')) for o in orders)
    return render_template('dashboard.html', orders=orders, settings=settings, total_sales=total)

@app.route('/add-order', methods=['POST'])
def add_order():
    if 'user' not in session: return redirect('/login')
    product_name = request.form.get('name', '')
    customer_name = request.form.get('customer_name', '')
    price = request.form.get('price', '0')
    
    data = {"manager_id": session['user'], "product_name": product_name, "customer_name": customer_name, "total_price": get_safe_float(price)}
    supabase.table("orders").insert(data).execute()
    
    # التنبيه
    s_res = supabase.table("settings").select("bot_token, telegram_chat_id").eq("manager_id", session['user']).maybe_single().execute()
    if s_res.data:
        token, chat_id = s_res.data.get('bot_token'), s_res.data.get('telegram_chat_id')
        if token and chat_id:
            msg = f"<b>طلب جديد!</b> 🛒\n\nالمنتج: {product_name}\nالزبون: {customer_name}\nالسعر: {price} دج"
            send_telegram_msg(token, chat_id, msg)
            
    flash("تمت إضافة الطلب بنجاح! ✅")
    return redirect('/dashboard')

@app.route('/edit-order', methods=['POST'])
def edit_order():
    if 'user' not in session: return redirect('/login')
    order_id = request.form.get('order_id')
    data = {"product_name": request.form.get('name'), "customer_name": request.form.get('customer_name'), "total_price": get_safe_float(request.form.get('price'))}
    supabase.table("orders").update(data).eq("id", order_id).execute()
    flash("تم تعديل الطلب بنجاح! ✏️")
    return redirect('/dashboard')

@app.route('/delete-order', methods=['POST'])
def delete_order():
    if 'user' not in session: return redirect('/login')
    order_id = request.form.get('order_id')
    if order_id: supabase.table("orders").delete().eq("id", order_id).execute()
    flash("تم حذف الطلب! 🗑️")
    return redirect('/dashboard')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user' not in session: return redirect('/login')
    manager_id = session['user']
    if request.method == 'POST':
        data = {"manager_id": manager_id}
        if request.form.get('shop_name'): data['shop_name'] = request.form.get('shop_name')
        if request.form.get('bot_token'): data['bot_token'] = request.form.get('bot_token')
        if request.form.get('telegram_chat_id'): data['telegram_chat_id'] = request.form.get('telegram_chat_id')
        if request.form.get('theme_color'): data['theme_color'] = request.form.get('theme_color')
        supabase.table("settings").upsert(data, on_conflict="manager_id").execute()
        flash("تم حفظ الإعدادات بنجاح! ⚙️")
        return redirect('/dashboard')
    
    res = supabase.table("settings").select("*").eq("manager_id", manager_id).maybe_single().execute()
    return render_template('settings.html', settings=res.data if res and res.data else {})

@app.route('/stats')
def stats():
    if 'user' not in session: return redirect('/login')
    s_res = supabase.table("settings").select("theme_color").eq("manager_id", session['user']).maybe_single().execute()
    settings = s_res.data if s_res and s_res.data else {"theme_color": "#4CAF50"}
    res = supabase.table("orders").select("*").eq("manager_id", session['user']).execute()
    orders = res.data if res and res.data else []
    labels = [o.get('product_name', 'طلب') for o in orders]
    values = [get_safe_float(o.get('total_price')) for o in orders]
    return render_template('stats.html', labels=labels, values=values, settings=settings)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
