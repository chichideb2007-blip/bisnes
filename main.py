import os
import telebot
from flask import Flask, render_template, request, redirect, session
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'your_secret_key_change_this'

# إعداد Supabase (يتم جلبه من إعدادات Render)
supabase = create_client(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_KEY'))

# --- دالة إرسال التنبيه ---
def send_telegram_order(manager_id, customer_name, product_name):
    settings = supabase.table("settings").select("bot_token", "telegram_chat_id").eq("manager_id", manager_id).single().execute().data
    if settings and settings.get('bot_token') and settings.get('telegram_chat_id'):
        try:
            bot = telebot.TeleBot(settings['bot_token'])
            text = f"🚨 طلب جديد!\n👤 الزبون: {customer_name}\n📦 المنتج: {product_name}"
            bot.send_message(settings['telegram_chat_id'], text)
        except Exception as e:
            print(f"خطأ في إرسال التنبيه: {e}")

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
    # جلب طلبات المدير الحالي فقط
    orders = supabase.table("orders").select("*").eq("manager_id", session['user']).execute().data
    return render_template('dashboard.html', orders=orders)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user' not in session: return redirect('/login')
    manager_id = session['user']
    
    if request.method == 'POST':
        data = {
            "manager_id": manager_id,
            "shop_name": request.form.get('shop_name'),
            "bot_token": request.form.get('bot_token'),
            "telegram_chat_id": request.form.get('telegram_chat_id')
        }
        supabase.table("settings").upsert(data).execute()
        return "تم حفظ الإعدادات بنجاح! <a href='/dashboard'>العودة للوحة التحكم</a>"
        
    settings = supabase.table("settings").select("*").eq("manager_id", manager_id).single().execute().data
    return render_template('settings.html', settings=settings if settings else {})

@app.route('/add-order', methods=['POST'])
def add_order():
    manager_id = request.form.get('manager_id')
    data = {
        "customer_name": request.form.get('customer_name'),
        "product_name": request.form.get('product_name'),
        "manager_id": manager_id
    }
    supabase.table("orders").insert(data).execute()
    send_telegram_order(manager_id, data['customer_name'], data['product_name'])
    return "تم تسجيل طلبك بنجاح!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
