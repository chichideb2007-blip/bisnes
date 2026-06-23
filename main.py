import os
import telebot
from flask import Flask, render_template, request, redirect, session
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'your_super_secret_key' # يفضل تغييره لشيء معقد

# إعداد الاتصال بـ Supabase
supabase = create_client(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_KEY'))

# --- الدوال البرمجية ---

def send_telegram_order(manager_id, customer_name, product_name):
    """إرسال إشعار للبوت الخاص بالمدير المعني"""
    settings = supabase.table("settings").select("bot_token", "telegram_chat_id").eq("manager_id", manager_id).single().execute().data
    if settings and settings.get('bot_token') and settings.get('telegram_chat_id'):
        try:
            bot = telebot.TeleBot(settings['bot_token'])
            text = f"🚨 طلب جديد!\n👤 الزبون: {customer_name}\n📦 المنتج: {product_name}"
            bot.send_message(settings['telegram_chat_id'], text)
        except Exception as e:
            print(f"خطأ في إرسال التنبيه: {e}")

# --- مسارات الموقع (Routes) ---

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # في نظام حقيقي، أضيفي هنا تحققاً من قاعدة البيانات
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
    
    # جلب طلبات المدير الحالي
    response = supabase.table("orders").select("*").eq("manager_id", session['user']).execute()
    orders = response.data if response.data else []
    
    # حساب مجموع المبيعات
    total_sales = sum(float(o.get('total_price', 0)) for o in orders)
    
    return render_template('dashboard.html', orders=orders, total_sales=total_sales)

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
    return redirect('/dashboard')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
