from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
# مفتاح سري للجلسات
app.secret_key = "shimo-secure-2026"

# إعداد Supabase (تأكدي من إضافة هذه المتغيرات في إعدادات Render)
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
        # منطق تسجيل الدخول
        session['user_id'] = "manager"
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'user_id' not in session: return redirect(url_for('login'))
    # جلب البيانات من Supabase
    res = supabase.table("orders").select("*").execute()
    return render_template('orders.html', orders=res.data)

@app.route('/stats')
def stats():
    if 'user_id' not in session: return redirect(url_for('login'))
    # جلب البيانات للإحصائيات
    res = supabase.table("orders").select("total_price, created_at").execute()
    return render_template('stats.html', orders=res.data)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('settings.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# دالة لحل مشكلة الخطأ 405/404 عند استدعاء روابط غير موجودة
@app.errorhandler(404)
def page_not_found(e):
    return "هذه الصفحة غير موجودة، تأكدي من الرابط!", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
