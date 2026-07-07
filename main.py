import os
from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'your_super_secret_key'

# إعداد Supabase مع التحقق من وجود المفاتيح
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

# التأكد من الاتصال بـ Supabase
try:
    supabase = create_client(url, key)
except Exception as e:
    print(f"خطأ في الاتصال بـ Supabase: {e}")
    supabase = None

# --- الروابط الأساسية ---

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# --- عمليات الطلبيات (التي تحتوي على أغلب الأخطاء) ---

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if not supabase:
        return "خطأ: قاعدة البيانات غير متصلة. يرجى التأكد من إعدادات Render.", 500

    if request.method == 'POST':
        try:
            data = {
                "customer_name": request.form.get("customer_name"),
                "customer_phone": request.form.get("customer_phone"),
                "product_name": request.form.get("product_name"),
                "total_price": float(request.form.get("total_price", 0)),
                "status": "قيد الانتظار"
            }
            supabase.table("orders").insert(data).execute()
        except Exception as e:
            return f"خطأ في حفظ البيانات: {str(e)}", 500
        return redirect(url_for('orders'))
    
    # جلب البيانات
    try:
        response = supabase.table("orders").select("*").execute()
        orders_list = response.data if response.data else []
    except Exception:
        orders_list = []
        
    return render_template('orders_dashboard.html', orders=orders_list)

@app.route('/delete_order/<int:order_id>')
def delete_order(order_id):
    if supabase:
        supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect(url_for('orders'))

@app.route('/update_order/<int:order_id>')
def update_order(order_id):
    if supabase:
        supabase.table("orders").update({"status": "تمت"}).eq("id", order_id).execute()
    return redirect(url_for('orders'))

# --- الصفحات الأخرى ---

@app.route('/stats')
def stats():
    return render_template('stats.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

if __name__ == '__main__':
    app.run(debug=True)
