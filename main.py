import os
from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# جلب الإعدادات من Render مع حماية ضد الخطأ
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

supabase = None
if url and key:
    supabase = create_client(url, key)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if not supabase:
        return "خطأ: قاعدة البيانات غير متصلة (تأكدي من إعدادات Render)", 500
    
    if request.method == 'POST':
        # الحصول على البيانات من النموذج
        data = {
            "customer_name": request.form.get("customer_name"),
            "phone": request.form.get("phone"),
            "product": request.form.get("product"),
            "price": float(request.form.get("price", 0))
        }
        # حفظ في قاعدة البيانات
        try:
            supabase.table("orders").insert(data).execute()
        except Exception as e:
            return f"خطأ في حفظ الطلبية: {str(e)}", 500
            
        return redirect(url_for('orders'))
    
    # جلب الطلبيات لعرضها
    try:
        response = supabase.table("orders").select("*").execute()
        orders_list = response.data
    except Exception:
        orders_list = []
        
    return render_template('orders_dashboard.html', orders=orders_list)

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/stats')
def stats():
    return render_template('stats.html')

if __name__ == '__main__':
    app.run(debug=True)
