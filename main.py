from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
import time

app = Flask(__name__)
app.secret_key = 'secret_key_123'

# إعداد Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# دالة لجلب معرف الشركة من الجلسة
def get_cid():
    return session.get('company_id')

# --- تسجيل حساب جديد (إنشاء شركة جديدة) ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # 1. إنشاء الحساب في Supabase Auth
        supabase.auth.sign_up({"email": email, "password": password})
        
        # 2. إنشاء معرف فريد لهذه الشركة (company_id)
        new_cid = f"comp_{int(time.time())}" 
        
        # 3. حفظ المعرف في جدول companies لربطه بالإيميل
        supabase.table("companies").insert({"email": email, "company_id": new_cid}).execute()
        
        return redirect(url_for('login'))
    return render_template('register.html')

# --- تسجيل الدخول (ربط الحساب بالـ company_id الخاص به) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            # التحقق من بيانات الدخول
            supabase.auth.sign_in_with_password({"email": email, "password": password})
            
            # جلب المعرف الخاص بهذا المستخدم من جدول companies
            res = supabase.table("companies").select("company_id").eq("email", email).execute()
            
            if res.data:
                session['company_id'] = res.data[0]['company_id']
                return redirect(url_for('dashboard'))
        except:
            return "خطأ في تسجيل الدخول!"
    return render_template('login.html')

# --- مسار المنتجات (العزل يحدث هنا) ---
@app.route('/products', methods=['GET', 'POST'])
def products():
    cid = get_cid()
    if not cid: return redirect(url_for('login'))

    if request.method == 'POST':
        data = {
            "name": request.form.get('name'),
            "quantity": int(request.form.get('quantity', 0)),
            "price": float(request.form.get('price', 0.0)),
            "company_id_text": cid  # نربط المنتج بالشركة فوراً
        }
        supabase.table("inventory").insert(data).execute()
        return redirect(url_for('products'))

    # نطلب فقط البيانات التي تطابق معرف الشركة الحالية
    res = supabase.table("inventory").select("*").eq("company_id_text", cid).execute()
    return render_template('products.html', products=res.data or [])

# --- مسار الطلبات (نفس مبدأ العزل) ---
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    cid = get_cid()
    if not cid: return redirect(url_for('login'))

    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "total_price": float(request.form.get('price', 0.0)),
            "company_id_text": cid # نربط الطلب بالشركة فوراً
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    res = supabase.table("orders").select("*").eq("company_id_text", cid).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
