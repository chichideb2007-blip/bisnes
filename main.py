from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from collections import defaultdict
from datetime import datetime
import os
import time

app = Flask(__name__)
app.secret_key = 'secret_key_123'

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/')
def index():
    return redirect(url_for('login'))

# --- مسار تسجيل حساب جديد ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # إنشاء حساب في Supabase Auth
        supabase.auth.sign_up({"email": email, "password": password})
        
        # إنشاء company_id فريد لهذه الشركة بناءً على الوقت
        new_company_id = f"comp_{int(time.time())}" 
        
        # حفظ الشركة في جدول الشركات لربطها بالبريد
        supabase.table("companies").insert({"email": email, "company_id": new_company_id}).execute()
        
        return redirect(url_for('login'))
    return render_template('register.html')

# --- مسار تسجيل الدخول ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            # التحقق من المستخدم في Supabase Auth
            supabase.auth.sign_in_with_password({"email": email, "password": password})
            
            # جلب الـ company_id المرتبط بهذا البريد من جدول companies
            res = supabase.table("companies").select("company_id").eq("email", email).execute()
            
            if res.data:
                # تخزين معرف الشركة في الجلسة لعزل البيانات
                session['company_id'] = res.data[0]['company_id']
                return redirect(url_for('dashboard'))
            else:
                return "لم يتم العثور على شركة مرتبطة بهذا البريد!"
                
        except Exception as e:
            return f"خطأ في تسجيل الدخول (تأكد من البريد وكلمة السر): {str(e)}"
            
    return render_template('login.html')

# --- لوحة التحكم ---
@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

# --- مسار المنتجات ---
@app.route('/products', methods=['GET', 'POST'])
def products():
    if 'company_id' not in session: return redirect(url_for('login'))
    
    if request.method == 'POST':
        data = {
            "name": request.form.get('name'),
            "quantity": int(request.form.get('quantity', 0)),
            "price": float(request.form.get('price', 0.0)),
            "company_id_text": session.get('company_id') 
        }
        supabase.table("inventory").insert(data).execute()
        return redirect(url_for('products'))

    res = supabase.table("inventory").select("*").eq("company_id_text", session.get('company_id')).execute()
    return render_template('products.html', products=res.data or [])

# --- مسار الطلبات ---
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'company_id' not in session: return redirect(url_for('login'))
    company_id = session['company_id']

    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('price', 0.0)),
            "company_id_text": company_id 
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    res = supabase.table("orders").select("*").eq("company_id_text", company_id).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

# --- مسار الإحصائيات ---
@app.route('/stats')
def show_stats():
    if 'company_id' not in session: return redirect(url_for('login'))
    company_id = session['company_id']
    try:
        res_orders = supabase.table("orders").select("total_price, created_at").eq("company_id_text", company_id).execute()
        orders = res_orders.data or []
        
        total_sales = sum(float(o.get('total_price', 0)) for o in orders)
        
        return render_template('stats.html', total_sales=total_sales, total_orders=len(orders))
    except Exception as e:
        return f"حدث خطأ في جلب البيانات: {str(e)}"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
