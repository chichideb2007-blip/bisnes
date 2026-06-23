import os
import threading
import telebot
from flask import Flask, render_template, request, redirect, session
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# إعداد Supabase
supabase = create_client(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_KEY'))

# إعداد البوت
bot = telebot.TeleBot(os.environ.get('BOT_TOKEN'))

# --- جزء البوت ---
@bot.message_handler(commands=['order'])
def order_from_bot(message):
    try:
        parts = message.text.split()
        if len(parts) < 4:
            bot.reply_to(message, "الصيغة الصحيحة: /order الاسم المنتج السعر")
            return
            
        data = {
            "customer_name": parts[1],
            "product_name": parts[2],
            "total_price": float(parts[3]),
            "manager_id": 1  # سيتم ربط الطلب بالمدير رقم 1 (يمكنك تغييرها لاحقاً)
        }
        supabase.table("orders").insert(data).execute()
        bot.reply_to(message, "✅ تم تسجيل الطلب في لوحة التحكم بنجاح!")
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {e}")

# --- جزء الموقع (Flask) ---
@app.route('/')
def home(): return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # (كود التحقق من المستخدم كما في ملفك القديم)
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/login')
    # جلب الطلبات
    orders = supabase.table("orders").select("*").execute().data
    total_sales = sum(float(o['total_price'] or 0) for o in orders)
    return render_template('dashboard.html', orders=orders, total_sales=total_sales)

if __name__ == '__main__':
    # تشغيل البوت في الخلفية (Thread)
    threading.Thread(target=lambda: bot.infinity_polling()).start()
    # تشغيل الموقع
    app.run(host='0.0.0.0', port=5000)
