import os
from flask import Flask, render_template, request, redirect, session
from supabase import create_client
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_super_secret_key'

# إعداد Supabase
supabase = create_client(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_KEY'))

# --- الدوال المساعدة ---
def get_safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

# --- المسارات ---
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
    
    # جلب البيانات بأمان
    s_res = supabase.table("settings").select("*").eq("manager_id", session['user']).maybe_single().execute()
    o_res = supabase.table("orders").select("*").eq("manager_id", session['user']).execute()
    
    settings = s_res.data if s_res and s_res.data else {"theme_color": "#4CAF50", "shop_name": "متجري"}
    orders = o_res.data if o_res and o_res.data else []
    
    # حساب إجمالي المبيعات بأمان
    total = sum(get_safe_float(o.get('total_price')) for o in orders)
    
    return render_template('dashboard.html', orders=orders, settings=settings, total_sales=total)

@app.route('/stats')
def stats():
    if 'user' not in session: return redirect('/login')
    
    s_res = supabase.table("settings").select("theme_color").eq("manager_id", session['user']).maybe_single().execute()
    settings = s_res.data if s_res and s_res.data else {"theme_color": "#4CAF50"}
    
    res = supabase.table("orders").select("*").eq("manager_id", session['user']).execute()
    orders = res.data if res and res.data else []
    
    # تجميع البيانات للمنحنى (الساعة)
    chart_data = {}
    for o in orders:
        # استخدام الوقت الحالي إذا كان created_at غير موجود
        date_str = o.get('created_at', datetime.now().isoformat())
        try:
            date_key = date_str[11:13] + ":00"
        except:
            date_key = "00:00"
        chart_data[date_key] = chart_data.get(date_key, 0) + get_safe_float(o.get('total_price'))
    
    return render_template('stats.html', 
                           labels=list(chart_data.keys()), 
                           values=list(chart_data.values()),
                           settings=settings)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user' not in session: return redirect('/login')
    if request.method == 'POST':
        data = {
            "manager_id": session['user'],
            "shop_name": request.form.get('shop_name', 'متجري'),
            "bot_token": request.form.get('bot_token', ''),
            "telegram_chat_id": request.form.get('telegram_chat_id', ''),
            "theme_color": request.form.get('theme_color', '#4CAF50')
        }
        supabase.table("settings").upsert(data).execute()
        return "تم حفظ الإعدادات! <a href='/dashboard'>العودة للوحة التحكم</a>"
    
    res = supabase.table("settings").select("*").eq("manager_id", session['user']).maybe_single().execute()
    return render_template('settings.html', settings=res.data if res and res.data else {})

@app.route('/add-product', methods=['POST'])
def add_product():
    if 'user' not in session: return redirect('/login')
    data = {
        "manager_id": session['user'],
        "product_name": request.form.get('name', 'منتج بدون اسم'),
        "total_price": get_safe_float(request.form.get('price'))
    }
    supabase.table("orders").insert(data).execute()
    return redirect('/dashboard')

@app.route('/delete-order', methods=['POST'])
def delete_order():
    if 'user' not in session: return redirect('/login')
    order_id = request.form.get('order_id')
    if order_id:
        supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect('/dashboard')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
