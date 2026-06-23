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
    # جلب الإعدادات من قاعدة البيانات
    res = supabase.table("settings").select("bot_token", "telegram_chat_id").eq("manager_id", manager_id).maybe_single().execute()
    
    # فحص الأمان: التأكد من وجود رد ووجود بيانات بداخل الرد
    if res and res.data:
        settings = res.data
        token = settings.get('bot_token')
        chat_id = settings.get('telegram_chat_id')
        
        # التأكد من أن التوكن والشات آي دي ليسا فارغين
        if token and chat_id:
            try:
                bot = telebot.TeleBot(token)
                bot.send_message(chat_id, f"🚨 طلب جديد!\n📦 المنتج: {product_name}")
            except Exception as e:
                print(f"خطأ في إرسال البوت: {e}")
    else:
        print("تنبيه: لا توجد إعدادات مضبوطة لهذا المستخدم في جدول settings")

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
    res = supabase.table("orders").select("*").eq("manager_id", session['user']).execute()
    orders = res.data if res and res.data else []
    total = sum(float(o.get('total_price', 0)) for o in orders)
    return render_template('dashboard.html', orders=orders, total_sales=total)

@app.route('/stats')
def stats():
    if 'user' not in session: return redirect('/login')
    res = supabase.table("orders").select("*").eq("manager_id", session['user']).execute()
    orders = res.data if res and res.data else []
    labels = [o.get('product_name') for o in orders]
    values = [float(o.get('total_price', 0)) for o in orders]
    return render_template('stats.html', labels=labels, values=values)

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
        return "تم الحفظ بنجاح! <a href='/dashboard'>العودة للوحة التحكم</a>"
    
    res = supabase.table("settings").select("*").eq("manager_id", manager_id).maybe_single().execute()
    # إرجاع قاموس فارغ إذا كانت البيانات غير موجودة لتجنب الانهيار
    settings_data = res.data if res and res.data else {}
    return render_template('settings.html', settings=settings_data)

@app.route('/add-product', methods=['POST'])
def add_product():
    if 'user' not in session: return redirect('/login')
    # إضافة المنتج لقاعدة البيانات
    data = {
        "manager_id": session['user'],
        "product_name": request.form.get('name'),
        "total_price": request.form.get('price'),
        "customer_name": "إضافة يدوية"
    }
    supabase.table("orders").insert(data).execute()
    # محاولة إرسال تنبيه تليجرام (لن ينهار الموقع إذا كانت البيانات ناقصة)
    send_telegram_order(session['user'], "إضافة يدوية", request.form.get('name'))
    return redirect('/dashboard')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
