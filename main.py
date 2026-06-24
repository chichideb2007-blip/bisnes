import os
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
from supabase import create_client, Client

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "shimo-saas-secure-2026")

# الذاكرة الاحتياطية لتأمين الحفظ الفوري للمديرين داخل السيرفر
if not hasattr(app, 'global_orders'):
    app.global_orders = []

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY")

supabase = None
if SUPABASE_URL and SUPABASE_KEY and "your-supabase" not in SUPABASE_URL:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Supabase init error: {e}")

def get_user_settings(user_id):
    if supabase:
        try:
            res = supabase.table("settings").select("*").eq("user_id", user_id).maybe_single().execute()
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

@app.route('/')
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        session['user_id'] = "manager_shimo_id"

    current_user_id = session['user_id']
    settings = get_user_settings(current_user_id)
    
    # جلب الطلبيات المخصصة للمدير الحالي فقط
    orders = []
    if supabase:
        try:
            orders_res = supabase.table("orders").select("*").eq("user_id", current_user_id).order("created_at", desc=True).execute()
            if orders_res and orders_res.data:
                orders = orders_res.data
        except Exception as e:
            print(f"Fallback to local memory due to fetch error: {e}")
            orders = [o for o in app.global_orders if o.get('user_id') == current_user_id]
    else:
        orders = [o for o in app.global_orders if o.get('user_id') == current_user_id]

    # حساب مجاميع الإحصائيات
    now = datetime.now()
    daily_total = 0.0
    monthly_total = 0.0
    yearly_total = 0.0

    for o in orders:
        try:
            price = float(o.get('total_price', 0) or 0)
            created_at_str = o.get('created_at', '')
            if created_at_str:
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

@app.route('/add-order', methods=['POST'])
def add_order():
    if 'user_id' not in session:
        return redirect(url_for('dashboard'))
        
    current_user_id = session['user_id']
    name = request.form.get('name')
    product = request.form.get('product')
    price_str = request.form.get('price', '0')
    phone = request.form.get('phone')
    
    try:
        price = float(price_str.strip()) if price_str else 0.0
    except ValueError:
        price = 0.0

    new_order = {
        "user_id": current_user_id,
        "customer_name": name,
        "product_name": product,
        "total_price": price,
        "customer_phone": phone,
        "created_at": datetime.utcnow().isoformat()
    }

    # حفظ محلي فوري لمنع أي تجمد في الصفحة وضمان بقاء الخانات محدثة للمدير
    app.global_orders.insert(0, new_order)

    # دفع البيانات متزامنة لـ Supabase
    if supabase:
        try:
            supabase.table("orders").insert(new_order).execute()
        except Exception as e:
            print(f"قاعدة البيانات مشغولة، تم التأمين محلياً: {e}")

    return redirect(url_for('dashboard'))

@app.route('/delete-order', methods=['POST'])
def delete_order():
    if 'user_id' not in session:
        return redirect(url_for('dashboard'))
        
    order_id = request.form.get('order_id')
    current_user_id = session['user_id']
    
    global_orders = [o for o in app.global_orders if not (o.get('user_id') == current_user_id and o.get('customer_name') == request.form.get('customer_name'))]
    
    if supabase and order_id:
        try:
            supabase.table("orders").delete().eq("id", order_id).eq("user_id", current_user_id).execute()
        except Exception as e:
            print(f"Error deleting order: {e}")
    return redirect(url_for('dashboard'))

@app.route('/update-info', methods=['POST'])
def update_info():
    if 'user_id' not in session:
        return redirect(url_for('dashboard'))
    current_user_id = session['user_id']
    updated_data = {
        "user_id": current_user_id,
        "shop_name": request.form.get('shop_name'),
        "telegram_bot_token": request.form.get('bot_token'),
        "telegram_chat_id": request.form.get('chat_id')
    }
    if supabase:
        try:
            res = supabase.table("settings").select("id").eq("user_id", current_user_id).maybe_single().execute()
            if res and res.data:
                supabase.table("settings").update(updated_data).eq("id", res.data["id"]).execute()
            else:
                supabase.table("settings").insert(updated_data).execute()
        except Exception as e:
            print(f"Error: {e}")
    return redirect(url_for('dashboard'))

@app.route('/update-colors', methods=['POST'])
def update_colors():
    if 'user_id' not in session:
        return redirect(url_for('dashboard'))
    current_user_id = session['user_id']
    updated_colors = {
        "user_id": current_user_id,
        "primary_color": request.form.get('primary_color'),
        "secondary_color": request.form.get('secondary_color')
    }
    if supabase:
        try:
            res = supabase.table("settings").select("id").eq("user_id", current_user_id).maybe_single().execute()
            if res and res.data:
                supabase.table("settings").update(updated_colors).eq("id", res.data["id"]).execute()
            else:
                supabase.table("settings").insert(updated_colors).execute()
        except Exception as e:
            print(f"Error: {e}")
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
