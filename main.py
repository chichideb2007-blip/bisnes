import os
import logging
from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client

# إعداد السجلات (Logs) لرؤية الأخطاء بوضوح
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'shimo-secret-key-2026')

# محاولة الاتصال بـ Supabase مع حماية
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')

if not url or not key:
    logger.error("خطأ: يرجى التأكد من إعدادات SUPABASE_URL و SUPABASE_KEY في Render!")
    supabase = None
else:
    try:
        supabase = create_client(url, key)
    except Exception as e:
        logger.error(f"خطأ في الاتصال بـ Supabase: {e}")
        supabase = None

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user_id'] = 'admin_user'
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if not supabase:
        return "خطأ: قاعدة البيانات غير متصلة. تأكدي من الإعدادات."
    
    if request.method == 'POST':
        try:
            data = {
                "customer_name": request.form.get('customer_name'),
                "product_name": request.form.get('product_name'),
                "total_price": float(request.form.get('total_price', 0))
            }
            supabase.table("orders").insert(data).execute()
        except Exception as e:
            logger.error(f"خطأ عند إضافة طلب: {e}")
        return redirect(url_for('orders'))
    
    res = supabase.table("orders").select("*").execute()
    return render_template('orders_dashboard.html', orders=res.data)

@app.route('/delete_order/<int:order_id>')
def delete_order(order_id):
    if supabase:
        supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect(url_for('orders'))

@app.route('/register')
def register():
    return render_template('register.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
