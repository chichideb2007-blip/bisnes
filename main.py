from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
from datetime import datetime
import json

app = Flask(__name__)
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

@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    
    if request.method == 'POST':
        try:
            prod_name = request.form.get("product")
            qty = 1 # نفترض بيع قطعة واحدة، يمكنكِ تعديلها من الـ form
            
            # 1. إضافة الطلبية
            new_order = {
                "customer_name": request.form.get("customer_name"),
                "product_name": prod_name,
                "total_price": float(request.form.get("price", 0)), 
                "company_id_text": comp_id,
                "status": "مكتملة"
            }
            supabase.table("orders").insert(new_order).execute()
            
            # 2. تحديث المخزن (نقص المنتج تلقائياً)
            # جلب المنتج الحالي
            product = supabase.table("inventory").select("*").eq("company_id_text", comp_id).eq("name", prod_name).single().execute()
            if product.data:
                new_qty = product.data['quantity'] - qty
                supabase.table("inventory").update({"quantity": new_qty}).eq("id", product.data['id']).execute()
            
            return redirect(url_for('orders'))
        except Exception as e:
            return f"خطأ في الإضافة أو تحديث المخزن: {e}"
    
    response = supabase.table("orders").select("*").eq("company_id_text", comp_id).execute()
    return render_template('orders_dashboard.html', orders=response.data or [])

@app.route('/stats')
def stats():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    try:
        response = supabase.table("orders").select("*").eq("company_id_text", comp_id).execute()
        orders = response.data or []
        
        # ترتيب البيانات
        yearly_stats = {}
        daily_total = 0
        today = datetime.now().date()
        
        for o in orders:
            price = float(o.get('total_price', 0))
            created_at = datetime.fromisoformat(o.get('created_at', datetime.now().isoformat()).replace('Z', ''))
            
            # حساب الإحصائيات
            year = str(created_at.year)
            yearly_stats[year] = yearly_stats.get(year, 0) + price
            
            if created_at.date() == today:
                daily_total += price

        return render_template('stats.html', 
                               yearly=json.dumps(dict(sorted(yearly_stats.items()))), 
                               daily_total=daily_total)
    except Exception as e:
        return f"خطأ في الإحصائيات: {e}"

# --- مسار استقبال رسائل إنستغرام (Webhook) ---
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return request.args.get('hub.challenge')
    
    # هنا يتم استقبال بيانات إنستغرام
    # يمكنك إضافة كود OpenAI هنا لتحليل الرسالة والرد عليها
    return 'OK', 200

if __name__ == '__main__':
    app.run(debug=True)
