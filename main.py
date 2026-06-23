import os
from flask import Flask, render_template, request, redirect, session
from supabase import create_client
import telebot

app = Flask(__name__)
app.secret_key = 'super-secret-key'

# إعداد Supabase
supabase = create_client(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_KEY'))

# إعداد البوت
bot = telebot.TeleBot(os.environ.get('BOT_TOKEN'))

# --- مسارات الموقع ---
@app.route('/')
def home(): return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = supabase.table("users").select("*").eq("username", request.form.get('username')).execute()
        if user.data and user.data[0]['password'] == request.form.get('password'):
            session['user'] = user.data[0]['id']
            return redirect('/dashboard')
    return render_template('login.html', is_register=False)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/login')
    orders = supabase.table("orders").select("*").execute().data
    total_sales = sum(float(o['price']) for o in orders)
    return render_template('dashboard.html', orders=orders, total_sales=total_sales)

@app.route('/delete-order/<int:order_id>')
def delete_order(order_id):
    supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

# --- دالة البوت لإضافة الطلب تلقائياً ---
@bot.message_handler(commands=['order'])
def handle_order(message):
    # مثال: الطلب يرسل بصيغة: /order اسم_الزبون المنتج السعر
    parts = message.text.split()
    if len(parts) == 4:
        data = {"customer_name": parts[1], "product_name": parts[2], "price": float(parts[3])}
        supabase.table("orders").insert(data).execute()
        bot.reply_to(message, "تم حفظ طلبك بنجاح في النظام!")

if __name__ == '__main__':
    # لتشغيل البوت والموقع معاً
    import threading
    threading.Thread(target=lambda: bot.infinity_polling()).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
