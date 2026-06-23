import os
import threading
import telebot
import requests
from flask import Flask, render_template, request, redirect, session
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# إعداد Supabase الأساسي (نستخدم الـ URL و KEY من إعدادات Render)
supabase = create_client(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_KEY'))

# --- وظيفة إرسال تنبيه للمدير ---
def notify_manager(manager_id, order_text):
    # جلب التوكين الخاص بهذه الشركة من جدول الإعدادات
    settings = supabase.table("settings").select("bot_token").eq("manager_id", manager_id).single().execute().data
    if settings and settings.get('bot_token'):
        token = settings['bot_token']
        # ملاحظة: نستخدم Chat ID ثابت للمدير أو نجلبه من الإعدادات
        # هنا للتسهيل نفترض أنكِ ستضيفين chat_id في جدول الإعدادات لاحقاً
        bot = telebot.TeleBot(token)
        bot.send_message(chat_id="ID_المدير_هنا", text=f"🚨 طلب جديد: {order_text}")

# --- صفحات الموقع ---
@app.route('/')
def home(): return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # (كود التحقق من المستخدم كما في ملفك الأصلي)
        # بعد التأكد، نحفظ manager_id في الـ session
        session['manager_id'] = "ID_المستخدم_المسجل" 
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/login')
    manager_id = session['user']
    # جلب طلبات هذه الشركة فقط
    orders = supabase.table("orders").select("*").eq("manager_id", manager_id).execute().data
    return render_template('dashboard.html', orders=orders)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user' not in session: return redirect('/login')
    manager_id = session['user']
    
    if request.method == 'POST':
        data = {
            "manager_id": manager_id,
            "bot_token": request.form.get('bot_token'),
            "shop_name": request.form.get('shop_name')
        }
        supabase.table("settings").upsert(data).execute()
        return "تم حفظ الإعدادات بنجاح!"
        
    current = supabase.table("settings").select("*").eq("manager_id", manager_id).single().execute().data
    return render_template('settings.html', settings=current)

@app.route('/add-order', methods=['POST'])
def add_order():
    # كود إضافة الطلب (نفس كودكِ القديم مع إضافة تنبيه للمدير)
    data = {
        "customer_name": request.form.get('customer_name'),
        "product_name": request.form.get('product_name'),
        "manager_id": request.form.get('manager_id')
    }
    supabase.table("orders").insert(data).execute()
    # إرسال تنبيه للمدير فوراً
    notify_manager(data['manager_id'], f"{data['customer_name']} طلب {data['product_name']}")
    return redirect('/dashboard')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
