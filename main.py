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

# --- دالة إرسال الإشعار عبر تيلجرام ---
def send_telegram_notification(comp_id, order_details):
    try:
        settings = supabase.table("company_settings").select("*").eq("company_id_text", comp_id).single().execute()
        if not settings.data: return

        telegram_token = settings.data.get('whatsapp_token')
        chat_id = settings.data.get('manager_phone')
        store_name = settings.data.get('store_name', 'متجرك')
        
        if not telegram_token or not chat_id: return

        url_api = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        body_text = (f"🔔 تنبيه طلبية جديدة من: {store_name}\n\n"
                     f"👤 العميل: {order_details['customer_name']}\n"
                     f"📞 الهاتف: {order_details['customer_phone']}\n"
                     f"📦 المنتج: {order_details['product_name']}\n"
                     f"💰 السعر: {order_details['total_price']} دج")
        
        payload = {"chat_id": chat_id, "text": body_text}
        requests.post(url_api, data=payload, timeout=5)
    except Exception as e:
        print(f"خطأ في إرسال التنبيه: {e}")

# --- المسارات ---

@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email, password = request.form.get('email'), request.form.get('password')
        user = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
        if user.data:
            session['company_id'] = str(user.data[0]['company_id'])
            return redirect(url_for('dashboard'))
        return "بيانات الدخول خاطئة"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'company_id' not in session: return redirect(url_for('login'))
    return render_template('settings.html')

@app.route('/update_settings', methods=['POST'])
def update_settings():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    
    data_to_save = {
        "store_name": request.form.get("store_name"),
        "whatsapp_token": request.form.get("token"),
        "manager_phone": request.form.get("phone")
    }
    
    try:
        supabase.table("company_settings").update(data_to_save).eq("company_id_text", comp_id).execute()
    except:
        data_to_save["company_id_text"] = comp_id
        supabase.table("company_settings").insert(data_to_save).execute()
        
    return "تم حفظ الإعدادات بنجاح! <a href='/dashboard'>العودة للوحة التحكم</a>"

@app.route('/orders', methods=['POST'])
def orders_post():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    
    try:
        product_name = request.form.get("product")
        customer_name = request.form.get("customer_name")
        customer_phone = request.form.get("customer_phone")
        total_price = float(request.form.get("price", 0))

        # 1. البحث عن المنتج في المخزن
        prod_query = supabase.table("inventory").select("*").eq("company_id_text", comp_id).eq("name", product_name).execute()
        
        if prod_query.data and len(prod_query.data) > 0:
            product = prod_query.data[0]
            
            if product['quantity'] >= 1:
                # 2. خصم الكمية
                supabase.table("inventory").update({"quantity": product['quantity'] - 1}).eq("id", product['id']).execute()
                
                # 3. حفظ الطلبية
                order_data = {
                    "customer_name": customer_name,
                    "customer_phone": customer_phone,
                    "product_name": product_name,
                    "total_price": total_price,
                    "company_id_text": comp_id
                }
                supabase.table("orders").insert(order_data).execute()
                
                # 4. إرسال التنبيه
                try: send_telegram_notification(comp_id, order_data)
                except: pass
                
                return redirect(url_for('orders'))
            else:
                return "خطأ: المنتج موجود ولكن الكمية صفر!"
        else:
            return f"خطأ: المنتج '{product_name}' غير موجود في المخزن! تأكدي من تطابق الاسم."
            
    except Exception as e:
        return f"<h1>خطأ أثناء حفظ الطلبية وتحديث المخزن:</h1><p>{str(e)}</p>"

@app.route('/orders')
def orders():
    if 'company_id' not in session: return redirect(url_for('login'))
    response = supabase.table("orders").select("*").eq("company_id_text", session['company_id']).execute()
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
        yearly_stats[str(created_at.year)] = yearly_stats.get(str(created_at.year), 0) + price
    return render_template('stats.html', yearly=json.dumps(dict(sorted(yearly_stats.items()))))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
