import os
from flask import Flask, render_template, request, redirect, session
from supabase import create_client
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_super_secret_key'

# إعداد Supabase
supabase = create_client(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_KEY'))

# دالة مساعدة للحماية من الأخطاء
def get_safe_float(value):
    try: return float(value)
    except: return 0.0

@app.route('/')
def home(): return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user'] = request.form.get('username')
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/login')
    s_res = supabase.table("settings").select("*").eq("manager_id", session['user']).maybe_single().execute()
    o_res = supabase.table("orders").select("*").eq("manager_id", session['user']).execute()
    
    settings = s_res.data if s_res and s_res.data else {"theme_color": "#4CAF50", "shop_name": "طلباتي"}
    orders = o_res.data if o_res and o_res.data else []
    total = sum(get_safe_float(o.get('total_price')) for o in orders)
    
    return render_template('dashboard.html', orders=orders, settings=settings, total_sales=total)

@app.route('/add-order', methods=['POST'])
def add_order():
    if 'user' not in session: return redirect('/login')
    data = {
        "manager_id": session['user'],
        "product_name": request.form.get('name', ''),
        "customer_name": request.form.get('customer_name', ''),
        "total_price": get_safe_float(request.form.get('price'))
    }
    supabase.table("orders").insert(data).execute()
    return redirect('/dashboard')

@app.route('/edit-order', methods=['POST'])
def edit_order():
    if 'user' not in session: return redirect('/login')
    order_id = request.form.get('order_id')
    data = {
        "product_name": request.form.get('name'),
        "customer_name": request.form.get('customer_name'),
        "total_price": get_safe_float(request.form.get('price'))
    }
    supabase.table("orders").update(data).eq("id", order_id).execute()
    return redirect('/dashboard')

@app.route('/delete-order', methods=['POST'])
def delete_order():
    if 'user' not in session: return redirect('/login')
    order_id = request.form.get('order_id')
    if order_id: supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect('/dashboard')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user' not in session: return redirect('/login')
    manager_id = session['user']
    if request.method == 'POST':
        data = {"manager_id": manager_id}
        if request.form.get('shop_name'): data['shop_name'] = request.form.get('shop_name')
        if request.form.get('theme_color'): data['theme_color'] = request.form.get('theme_color')
        supabase.table("settings").upsert(data, on_conflict="manager_id").execute()
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
    
    # تحضير بيانات المنحنى
    labels = [o.get('created_at', datetime.now().isoformat())[11:13] + ":00" for o in orders]
    values = [get_safe_float(o.get('total_price')) for o in orders]
    
    return render_template('stats.html', labels=labels, values=values, settings=settings)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
