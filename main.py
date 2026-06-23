import os
import telebot
from flask import Flask, render_template, request, redirect, session
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'your_super_secret_key'

# إعداد Supabase
supabase = create_client(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_KEY'))

# --- الدالة الآمنة لإرسال التليجرام ---
def send_telegram_order(manager_id, customer_name, product_name):
    res = supabase.table("settings").select("bot_token", "telegram_chat_id").eq("manager_id", manager_id).maybe_single().execute()
    if res and res.data:
        settings = res.data
        if settings.get('bot_token') and settings.get('telegram_chat_id'):
            try:
                bot = telebot.TeleBot(settings['bot_token'])
                bot.send_message(settings['telegram_chat_id'], f"🚨 طلب جديد!\n📦 المنتج: {product_name}")
            except: pass

# --- المسارات ---
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
    # جلب الإعدادات (ليتم استخدام اللون في القالب)
    settings = supabase.table("settings").select("*").eq("manager_id", session['user']).maybe_single().execute()
    user_settings = settings.data if settings and settings.data else {}
    
    orders = supabase.table("orders").select("*").eq("manager_id", session['user']).execute()
    orders_list = orders.data if orders and orders.data else []
    return render_template('dashboard.html', orders=orders_list, settings=user_settings)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user' not in session: return redirect('/login')
    manager_id = session['user']
    if request.method == 'POST':
        data = {
            "manager_id": manager_id,
            "shop_name": request.form.get('shop_name'),
            "bot_token": request.form.get('bot_token'),
            "telegram_chat_id": request.form.get('telegram_chat_id'),
            "theme_color": request.form.get('theme_color') # حفظ اللون الجديد
        }
        supabase.table("settings").upsert(data).execute()
        return "تم الحفظ! <a href='/dashboard'>العودة</a>"
    
    res = supabase.table("settings").select("*").eq("manager_id", manager_id).maybe_single().execute()
    return render_template('settings.html', settings=res.data if res and res.data else {})

@app.route('/add-product', methods=['POST'])
def add_product():
    if 'user' not in session: return redirect('/login')
    data = {
        "manager_id": session['user'],
        "product_name": request.form.get('name'),
        "total_price": request.form.get('price'),
        "customer_name": "إضافة يدوية"
    }
    supabase.table("orders").insert(data).execute()
    send_telegram_order(session['user'], "إضافة يدوية", request.form.get('name'))
    return redirect('/dashboard')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
