from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
import requests
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here")

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- دالة إرسال إشعار واتساب (تعتمد على إعدادات الشركة) ---
def send_whatsapp_notification(comp_id, order_details):
    # جلب بيانات الشركة الخاصة من قاعدة البيانات
    settings = supabase.table("company_settings").select("*").eq("company_id_text", comp_id).single().execute()
    
    if not settings.data:
        print(f"لا توجد إعدادات واتساب للشركة: {comp_id}")
        return

    instance_id = settings.data['whatsapp_instance']
    token = settings.data['whatsapp_token']
    manager_phone = settings.data['manager_phone']
    
    url_api = f"https://api.ultramsg.com/{instance_id}/messages/chat"
    
    body_text = (f"🔔 تنبيه طلبية جديدة!\n\n"
                 f"👤 العميل: {order_details['customer_name']}\n"
                 f"📞 الهاتف: {order_details['customer_phone']}\n"
                 f"📦 المنتج: {order_details['product_name']}\n"
                 f"💰 السعر: {order_details['total_price']} دج")
    
    payload = {"token": token, "to": manager_phone, "body": body_text}
    requests.post(url_api, data=payload)

# --- المسارات ---

@app.route('/update_settings', methods=['POST'])
def update_settings():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    new_settings = {
        "company_id_text": comp_id,
        "whatsapp_instance": request.form.get("instance_id"),
        "whatsapp_token": request.form.get("token"),
        "manager_phone": request.form.get("phone")
    }
    # upsert يقوم بالتحديث إذا كانت البيانات موجودة أو الإضافة إذا كانت جديدة
    supabase.table("company_settings").upsert(new_settings).execute()
    return "تم حفظ الإعدادات بنجاح! <a href='/dashboard'>العودة</a>"

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    
    if request.method == 'POST':
        try:
            order_data = {
                "customer_name": request.form.get("customer_name"),
                "customer_phone": request.form.get("customer_phone"),
                "product_name": request.form.get("product"),
                "total_price": float(request.form.get("price", 0)),
                "company_id_text": comp_id,
                "status": "مكتملة"
            }
            
            prod_query = supabase.table("inventory").select("*").eq("company_id_text", comp_id).eq("name", order_data["product_name"]).single().execute()
            
            if prod_query.data and prod_query.data['quantity'] >= 1:
                supabase.table("inventory").update({"quantity": prod_query.data['quantity'] - 1}).eq("id", prod_query.data['id']).execute()
                supabase.table("orders").insert(order_data).execute()
                
                # إرسال الإشعار باستخدام دالة الإعدادات الذكية
                send_whatsapp_notification(comp_id, order_data)
                
            return redirect(url_for('orders'))
        except Exception as e:
            return f"خطأ: {e}"
    
    response = supabase.table("orders").select("*").eq("company_id_text", comp_id).execute()
    return render_template('orders_dashboard.html', orders=response.data or [])

# ... (باقي المسارات مثل login, dashboard, stats تبقى كما هي) ...

if __name__ == '__main__':
    app.run(debug=True)
