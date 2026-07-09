from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
import requests
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

# إعداد Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- دالة إرسال إشعار واتساب ---
def send_whatsapp_notification(manager_phone, order_details):
    # ضعي هنا بياناتك من موقع Ultramsg
    instance_id = "instanceXXXXX" 
    token = "YOUR_TOKEN_HERE"
    url_api = f"https://api.ultramsg.com/{instance_id}/messages/chat"
    
    payload = {
        "token": token,
        "to": manager_phone,
        "body": (f"🔔 تنبيه طلبية جديدة!\n\n"
                 f"العميل: {order_details['customer_name']}\n"
                 f"المنتج: {order_details['product_name']}\n"
                 f"السعر: {order_details['total_price']} دج")
    }
    try:
        response = requests.post(url_api, data=payload)
        return response.json()
    except Exception as e:
        print(f"خطأ في إرسال واتساب: {e}")
        return None

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

@app.route('/settings')
def settings():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('settings.html')

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    
    if request.method == 'POST':
        try:
            prod_name = request.form.get("product")
            cust_name = request.form.get("customer_name")
            price = request.form.get("price")
            qty_sold = 1 
            
            # 1. التحقق من المخزون
            prod_query = supabase.table("inventory").select("*").eq("company_id_text", comp_id).eq("name", prod_name).single().execute()
            
            if prod_query.data and prod_query.data['quantity'] >= qty_sold:
                # تحديث المخزن
                new_qty = prod_query.data['quantity'] - qty_sold
                supabase.table("inventory").update({"quantity": new_qty}).eq("id", prod_query.data['id']).execute()
                
                # 2. إضافة الطلبية
                order_data = {
                    "customer_name": cust_name,
                    "product_name": prod_name,
                    "total_price": float(price),
                    "company_id_text": comp_id,
                    "status": "مكتملة"
                }
                supabase.table("orders").insert(order_data).execute()
                
                # 3. إرسال إشعار واتساب للمدير (ضعي رقمك هنا بصيغة دولية بدون +)
                send_whatsapp_notification("213XXXXXXXXX", order_data)
                
            else:
                return "خطأ: المنتج غير متوفر!"
            
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
        created_at = datetime.fromisoformat(o.get('created_at', datetime.now().isoformat()).replace('Z', ''))
        year = str(created_at.year)
        yearly_stats[year] = yearly_stats.get(year, 0) + price

    return render_template('stats.html', yearly=json.dumps(dict(sorted(yearly_stats.items()))))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
