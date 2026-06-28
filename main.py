from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
# مفتاح سري للجلسات
app.secret_key = "shimo-secure-2026"

# إعداد Supabase (تأكدي من إضافة هذه المتغيرات في إعدادات Render - Environment)
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key)

# --- المسارات ---

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # منطق التحقق (مبدئياً)
        session['user_id'] = "manager"
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# المسار الذي كان يسبب الخطأ في login.html
@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'user_id' not in session: return redirect(url_for('login'))
    # جلب البيانات الحقيقية من Supabase
    res = supabase.table("orders").select("*").execute()
    return render_template('orders.html', orders=res.data)

@app.route('/stats')
def stats():
    if 'user_id' not in session: return redirect(url_for('login'))
    # جلب البيانات للإحصائيات الحقيقية
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
