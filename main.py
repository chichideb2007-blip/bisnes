import os
import requests
from flask import Flask, render_template, request, redirect, session, flash
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'shimo_secret_key_2026'

supabase = create_client(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_KEY'))

# --- الدوال المساعدة ---
def send_telegram_msg(token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})
    except: pass

# --- الرد الذكي على الزبائن (تأكيد الطلب) ---
@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if 'message' in update:
        chat_id = update['message']['chat']['id']
        text = update['message'].get('text', '').lower()
        
        # مثال: إذا كتب الزبون "شراء [اسم المنتج]"
        if "شراء" in text:
            p_name = text.replace("شراء", "").strip()
            # 1. البحث عن المنتج والكمية
            prod = supabase.table("products").select("*").ilike("name", f"%{p_name}%").maybe_single().execute()
            
            if prod.data and prod.data['stock_quantity'] > 0:
                # 2. خصم الكمية (تحديث المخزن)
                new_stock = prod.data['stock_quantity'] - 1
                supabase.table("products").update({"stock_quantity": new_stock}).eq("id", prod.data['id']).execute()
                
                # 3. تسجيل الطلب
                supabase.table("orders").insert({
                    "product_name": prod.data['name'],
                    "total_price": prod.data['price'],
                    "customer_name": "زبون تليجرام"
                }).execute()
                
                reply = f"تم تأكيد طلبك لـ {prod.data['name']} بنجاح! السعر: {prod.data['price']} دج."
            else:
                reply = "عذراً، المنتج غير متوفر أو نفدت الكمية."
            
            # إرسال التنبيه
            s_res = supabase.table("settings").select("bot_token").limit(1).execute()
            if s_res.data: send_telegram_msg(s_res.data[0]['bot_token'], chat_id, reply)
            
    return "ok", 200

# --- لوحة التحكم ---
@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/login')
    # جلب المنتجات والطلبات
    prods = supabase.table("products").select("*").execute().data
    orders = supabase.table("orders").select("*").execute().data
    return render_template('dashboard.html', products=prods, orders=orders)

@app.route('/add-product', methods=['POST'])
def add_product():
    data = {
        "name": request.form.get('name'),
        "price": float(request.form.get('price')),
        "stock_quantity": int(request.form.get('stock'))
    }
    supabase.table("products").insert(data).execute()
    flash("تم إضافة المنتج للمخزن! 📦")
    return redirect('/dashboard')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
