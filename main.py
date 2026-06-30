from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = "shimo_secure_key_2026"

# إعدادات Supabase - تأكدي من وجود SUPABASE_URL و SUPABASE_KEY في إعدادات Render
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# 1. مسار تسجيل الدخول
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# 2. لوحة التحكم
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# 3. مسار الطلبيات (إضافة + عرض)
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        try:
            data = {
                "customer_name": request.form.get('customer_name'),
                "product_name": request.form.get('product_name'),
                "total_price": float(request.form.get('total_price', 0)),
                "customer_phone": request.form.get('customer_phone')
            }
            supabase.table("orders").insert(data).execute()
        except Exception as e:
            print(f"Error saving order: {e}")
        return redirect(url_for('orders'))
    
    response = supabase.table("orders").select("*").execute()
    return render_template('orders_dashboard.html', orders=response.data)

# 4. مسار حذف الطلبية
@app.route('/delete_order/<int:order_id>')
def delete_order(order_id):
    supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect(url_for('orders'))

# 5. مسار الإحصائيات (أوتوماتيكي)
@app.route('/stats')
def stats():
    response = supabase.table("orders").select("total_price").execute()
    # حساب المجموع أوتوماتيكياً
    total_sales = sum(float(o.get('total_price', 0)) for o in response.data)
    return render_template('stats.html', total_sales=total_sales)

# 6. مسار الإعدادات
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    return render_template('settings.html')

# 7. تسجيل الخروج
@app.route('/logout')
def logout():
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
