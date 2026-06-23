import os
from flask import Flask, render_template, request, redirect, session
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'shimo_super_pro_2026'

url = os.environ.get('SUPABASE_URL', '')
key = os.environ.get('SUPABASE_KEY', '')
supabase = create_client(url, key) if url and key else None

# --- المسارات ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user'] = request.form.get('username')
        return redirect('/orders')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

@app.route('/orders')
def manage_orders():
    if 'user' not in session: return redirect('/login')
    
    # جلب طلبات هذا المدير فقط
    orders = supabase.table("orders").select("*").eq("manager_email", session['user']).execute().data if supabase else []
    # حساب الإحصائيات (مجموع الأرباح)
    total_today = sum(float(o.get('price', 0)) for o in orders)
    
    return render_template('orders_dashboard.html', orders=orders, total=total_today)

@app.route('/add-order', methods=['POST'])
def add_order():
    if 'user' not in session: return redirect('/login')
    supabase.table("orders").insert({
        "customer_name": request.form.get('name'),
        "order_details": request.form.get('details'),
        "price": float(request.form.get('price', 0)),
        "manager_email": session['user']
    }).execute()
    return redirect('/orders')

@app.route('/delete-order/<int:order_id>')
def delete_order(order_id):
    supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect('/orders')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user' not in session: return redirect('/login')
    if request.method == 'POST':
        # حفظ إعدادات المدير (اسم المتجر، البوت، اللون)
        supabase.table("managers").upsert({
            "email": session['user'],
            "store_name": request.form.get('store_name'),
            "bot_token": request.form.get('bot_token'),
            "theme_color": request.form.get('theme_color')
        }).execute()
    return render_template('settings.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
