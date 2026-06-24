import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime
from supabase import create_client, Client

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-key-shimo")

# 1. الاتصال بقاعدة بيانات Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    # قيم احتياطية محلياً في حال عدم ضبط المتغيرات في Render بعد
    SUPABASE_URL = "https://your-supabase-url.supabase.co"
    SUPABASE_KEY = "your-supabase-anon-key"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# دالة مساعدة لجلب إعدادات المتجر والألوان
def get_settings():
    try:
        res = supabase.table("settings").select("*").maybe_single().execute()
        if res and res.data:
            return res.data
    except Exception as e:
        print(f"Error fetching settings: {e}")
    
    return {
        "shop_name": "متجري الاحترافي",
        "telegram_bot_token": "",
        "telegram_chat_id": "",
        "primary_color": "#a855f7",
        "secondary_color": "#7e22ce"
    }

# ==================== المسارات (Routes) ====================

@app.route('/')
@app.route('/dashboard')
def dashboard():
    settings = get_settings()
    
    try:
        orders_res = supabase.table("orders").select("*").order("created_at", desc=True).execute()
        orders = orders_res.data if orders_res and orders_res.data else []
    except Exception as e:
        print(f"Error fetching orders: {e}")
        orders = []

    # حساب الإحصائيات الحقيقية بناءً على تاريخ اليوم الفعلي
    now = datetime.now()
    daily_total = 0.0
    monthly_total = 0.0
    yearly_total = 0.0

    for o in orders:
        price = float(o.get('total_price', 0) or 0)
        created_at_str = o.get('created_at', '')
        
        if created_at_str:
            try:
                clean_date_str = created_at_str.split('.')[0].replace('Z', '').replace('T', ' ')
                order_date = datetime.strptime(clean_date_str, "%Y-%m-%d %H:%M:%S")
                
                if order_date.date() == now.date():
                    daily_total += price
                if order_date.year == now.year and order_date.month == now.month:
                    monthly_total += price
                if order_date.year == now.year:
                    yearly_total += price
            except Exception as ex:
                print(f"Date parsing error: {ex}")

    return render_template(
        'dashboard.html', 
        orders=orders, 
        settings=settings,
        daily_total=round(daily_total, 2),
        monthly_total=round(monthly_total, 2),
        yearly_total=round(yearly_total, 2)
    )

# مسار إضافة وتأكيد الطلبية (مطابق تماماً لحقول الـ HTML)
@app.route('/add-order', methods=['POST'])
def add_order():
    name = request.form.get('name')
    product = request.form.get('product')
    price_str = request.form.get('price', '0')
    phone = request.form.get('phone')
    
    try:
        price = float(price_str.strip()) if price_str else 0.0
    except ValueError:
        price = 0.0

    new_order = {
        "customer_name": name,
        "product_name": product,
        "total_price": price,
        "customer_phone": phone,
        "created_at": datetime.utcnow().isoformat()
    }

    try:
        supabase.table("orders").insert(new_order).execute()
        print("✅ تم حفظ الطلبية بنجاح")
    except Exception as e:
        print(f"❌ خطأ أثناء الحفظ في جدول Supabase: {e}")

    return redirect(url_for('dashboard'))

@app.route('/edit-order', methods=['POST'])
def edit_order():
    return redirect(url_for('dashboard'))

@app.route('/delete-order', methods=['POST'])
def delete_order():
    order_id = request.form.get('order_id')
    if order_id:
        try:
            supabase.table("orders").delete().eq("id", order_id).execute()
        except Exception as e:
            print(f"Error deleting order: {e}")
    return redirect(url_for('dashboard'))

@app.route('/update-info', methods=['POST'])
def update_info():
    shop_name = request.form.get('shop_name')
    bot_token = request.form.get('bot_token')
    chat_id = request.form.get('chat_id')

    updated_data = {
        "shop_name": shop_name,
        "telegram_bot_token": bot_token,
        "telegram_chat_id": chat_id
    }

    try:
        res = supabase.table("settings").select("id").maybe_single().execute()
        if res and res.data:
            supabase.table("settings").update(updated_data).eq("id", res.data["id"]).execute()
        else:
            supabase.table("settings").insert(updated_data).execute()
    except Exception as e:
        print(f"Error updating info: {e}")
    return redirect(url_for('dashboard'))

@app.route('/update-colors', methods=['POST'])
def update_colors():
    primary_color = request.form.get('primary_color')
    secondary_color = request.form.get('secondary_color')

    updated_colors = {
        "primary_color": primary_color,
        "secondary_color": secondary_color
    }

    try:
        res = supabase.table("settings").select("id").maybe_single().execute()
        if res and res.data:
            supabase.table("settings").update(updated_colors).eq("id", res.data["id"]).execute()
        else:
            supabase.table("settings").insert(updated_colors).execute()
    except Exception as e:
        print(f"Error updating colors: {e}")
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
