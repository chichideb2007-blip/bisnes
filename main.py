from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
from datetime import datetime

app = Flask(__name__)
# مفتاح سري للتشفير
app.secret_key = "shimo-secure-2026"

# إعداد Supabase (تأكدي من إضافة هذه المتغيرات في إعدادات Render Environment)
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key)

# --- المسارات (Routes) ---

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # في الحقيقة يتم التحقق هنا من قاعدة البيانات
        session['user_id'] = "manager_shimo_id"
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/orders')
def orders():
    if 'user_id' not in session: return redirect(url_for('login'))
    # جلب الطلبات من Supabase
    res = supabase.table("orders").select("*").execute()
    return render_template('orders.html', orders=res.data)

@app.route('/stats')
def stats():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('stats.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('settings.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    # تأكدي أن المنفذ 5000 هو الافتراضي
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
