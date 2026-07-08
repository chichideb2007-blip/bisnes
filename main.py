from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
from datetime import datetime

app = Flask(__name__)
# تأكدي من تغيير هذا المفتاح إلى نص عشوائي طويل
app.secret_key = 'your_super_secret_key_123'

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- المسارات ---

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            user = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
            if user.data:
                session['company_id'] = user.data[0]['company_id']
                return redirect(url_for('dashboard'))
            return "بيانات الدخول خاطئة"
        except Exception as e:
            return f"حدث خطأ: {e}"
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        new_user = {
            "email": request.form.get('email'),
            "password": request.form.get('password'),
            "company_id": request.form.get('company_id')
        }
        supabase.table("users").insert(new_user).execute()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    
    if request.method == 'POST':
        # حفظ الطلبية الجديدة
        order_data = {
            "customer_name": request.form.get("customer_name"),
            "product": request.form.get("product"),
            "price": float(request.form.get("price", 0)),
            "company_id": comp_id,
            "created_at": datetime.now().isoformat()
        }
        supabase.table("orders").insert(order_data).execute()
        return redirect(url_for('orders'))

    # عرض الطلبات
    response = supabase.table("orders").select("*").eq("company_id", comp_id).execute()
    return render_template('orders_dashboard.html', orders=response.data)

@app.route('/stats')
def stats():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    response = supabase.table("orders").select("*").eq("company_id", comp_id).execute()
    return render_template('stats.html', orders=response.data)

@app.route('/settings')
def settings():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('settings.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
