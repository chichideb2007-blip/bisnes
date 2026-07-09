from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
from datetime import datetime
import json

app = Flask(__name__)
# تأكدي من إعداد SECRET_KEY في إعدادات Render (Environment Variables)
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
            if user.data and len(user.data) > 0:
                session['company_id'] = str(user.data[0]['company_id'])
                return redirect(url_for('dashboard'))
            return "بيانات الدخول خاطئة"
        except Exception as e:
            return f"خطأ في الاتصال: {e}"
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            new_user = {
                "email": request.form.get('email'),
                "password": request.form.get('password'),
                "company_id": request.form.get('company_id')
            }
            supabase.table("users").insert(new_user).execute()
            return "تم التسجيل بنجاح! <a href='/login'>العودة لتسجيل الدخول</a>"
        except Exception as e:
            return f"خطأ في التسجيل: {e}"
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

# المسار الخاص بالإعدادات (تمت إضافته لحل خطأ الـ BuildError)
@app.route('/settings')
def settings():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('settings.html')

# المسار الذكي: إضافة طلبية + خصم تلقائي من المخزون
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    
    if request.method == 'POST':
        try:
            prod_name = request.form.get("product")
            qty_sold = 1 
            
            # 1. التحقق من المخزون وخصمه
            prod_query = supabase.table("inventory").select("*").eq("company_id_text", comp_id).eq("name", prod_name).single().execute()
            
            if prod_query.data and prod_query.data['quantity'] >= qty_sold:
                new_qty = prod_query.data['quantity'] - qty_sold
                supabase.table("inventory").update({"quantity": new_qty}).eq("id", prod_query.data['id']).execute()
                
                # 2. إضافة الطلبية
                supabase.table("orders").insert({
                    "customer_name": request.form.get("customer_name"),
                    "product_name": prod_name,
                    "total_price": float(request.form.get("price", 0)),
                    "company_id_text": comp_id,
                    "status": "مكتملة"
                }).execute()
            else:
                return "خطأ: المنتج غير متوفر أو غير موجود في مخزنك!"
            
            return redirect(url_for('orders'))
        except Exception as e:
            return f"خطأ في العملية: {e}"
    
    response = supabase.table("orders").select("*").eq("company_id_text", comp_id).execute()
    return render_template('orders_dashboard.html', orders=response.data or [])

@app.route('/delete_order/<int:order_id>')
def delete_order(order_id):
    if 'company_id' not in session: return redirect(url_for('login'))
    supabase.table("orders").delete().eq("id", order_id).eq("company_id_text", session['company_id']).execute()
    return redirect(url_for('orders'))

@app.route('/stats')
def stats():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    response = supabase.table("orders").select("*").eq("company_id_text", comp_id).execute()
    orders = response.data or []
    
    yearly_stats = {}
    for o in orders:
        price = float(o.get('total_price', 0))
        # استخدام التاريخ الفعلي للطلبية
        created_at = datetime.fromisoformat(o.get('created_at', datetime.now().isoformat()).replace('Z', ''))
        year = str(created_at.year)
        yearly_stats[year] = yearly_stats.get(year, 0) + price

    return render_template('stats.html', yearly=json.dumps(dict(sorted(yearly_stats.items()))))

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return request.args.get('hub.challenge')
    return 'OK', 200

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
