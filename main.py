from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
# تأكدي من إعداد SECRET_KEY في إعدادات Render
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

# إعداد Supabase
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
                session['company_id'] = str(user.data[0]['company_id'])
                return redirect(url_for('dashboard'))
            return "بيانات الدخول خاطئة"
        except Exception as e:
            return f"خطأ في الاتصال: {e}"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    
    if request.method == 'POST':
        new_order = {
            "customer_name": request.form.get("customer_name"),
            "product": request.form.get("product"),
            "price": request.form.get("price"),
            "company_id_text": comp_id 
        }
        supabase.table("orders").insert(new_order).execute()
        return redirect(url_for('orders'))
    
    response = supabase.table("orders").select("*").eq("company_id_text", comp_id).execute()
    return render_template('orders_dashboard.html', orders=response.data or [])

@app.route('/stats')
def stats():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    
    try:
        # جلب البيانات بالعمود الجديد
        response = supabase.table("orders").select("*").eq("company_id_text", comp_id).execute()
        orders_data = response.data or []
        
        # إرسال متغيرات فارغة لتجنب انهيار stats.html
        return render_template('stats.html', 
                               orders=orders_data, 
                               daily={}, 
                               monthly={}, 
                               yearly={})
    except Exception as e:
        return f"خطأ في تحميل الإحصائيات: {e}"

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
