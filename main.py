import os
from flask import Flask, render_template, request, redirect, session
from supabase import create_client
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_super_secret_key'

# إعداد Supabase
supabase = create_client(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_KEY'))

# دالة مساعدة لتجنب الأخطاء
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

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/login')
    s_res = supabase.table("settings").select("*").eq("manager_id", session['user']).maybe_single().execute()
    o_res = supabase.table("orders").select("*").eq("manager_id", session['user']).execute()
    
    settings = s_res.data if s_res and s_res.data else {"theme_color": "#4CAF50", "shop_name": "متجري"}
    orders = o_res.data if o_res and o_res.data else []
    total = sum(get_safe_float(o.get('total_price')) for o in orders)
    
    return render_template('dashboard.html', orders=orders, settings=settings, total_sales=total)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user' not in session: return redirect('/login')
    manager_id = session['user']
    if request.method == 'POST':
        # تحديث الحقول بمرونة
        data = {
            "manager_id": manager_id,
            "shop_name": request.form.get('shop_name', ''),
            "bot_token": request.form.get('bot_token', ''),
            "telegram_chat_id": request.form.get('telegram_chat_id', ''),
            "theme_color": request.form.get('theme_color', '#4CAF50')
        }
        supabase.table("settings").upsert(data, on_conflict="manager_id").execute()
        return redirect('/dashboard')
    
    res = supabase.table("settings").select("*").eq("manager_id", manager_id).maybe_single().execute()
    return render_template('settings.html', settings=res.data if res and res.data else {})

# ... باقي الدوال (add_product, delete_order, stats) تبقى كما هي ...
