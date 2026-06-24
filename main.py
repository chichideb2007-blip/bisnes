import os
from flask import Flask, render_template, request, session, redirect
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'shimo_ultimate_fixed_2026'

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key) if url and key else None

def get_or_create_settings():
    """دالة ذكية لجلب الإعدادات أو إنشائها فوراً إذا كانت غير موجودة لتجنب الـ None"""
    default_settings = {
        "id": 1,
        "shop_name": "متجري الإلكتروني",
        "telegram_bot_token": "",
        "telegram_chat_id": "",
        "primary_color": "#7a3e13",
        "secondary_color": "#bd6a2c"
    }
    if not supabase:
        return default_settings
    try:
        # فحص وجود السطر رقم 1
        res = supabase.table("settings").select("*").eq("id", 1).execute()
        if res.data and len(res.data) > 0:
            db_set = res.data[0]
            # التأكد من ملء الفراغات إذا كانت قيمتها None في القاعدة
            return {
                "id": 1,
                "shop_name": db_set.get("shop_name") or "متجري الإلكتروني",
                "telegram_bot_token": db_set.get("telegram_bot_token") or "",
                "telegram_chat_id": db_set.get("telegram_chat_id") or "",
                "primary_color": db_set.get("primary_color") or "#7a3e13",
                "secondary_color": db_set.get("secondary_color") or "#bd6a2c"
            }
        else:
            # إذا لم يجد السطر، يقوم بإنشائه فوراً بقيم افتراضية
            supabase.table("settings").insert(default_settings).execute()
            return default_settings
    except Exception as e:
        print(f"Error in get_or_create_settings: {e}")
        return default_settings

@app.route('/')
def index(): 
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user'] = request.form.get('username')
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/dashboard', methods=['GET'])
def dashboard():
    if 'user' not in session: 
        return redirect('/login')
    
    orders = []
    # جلب الإعدادات المؤمنة بدون None
    settings = get_or_create_settings()
    
    if supabase:
        try:
            response_orders = supabase.table("orders").select("*").execute()
            orders = response_orders.data if response_orders.data else []
        except Exception as e: 
            print(f"Error fetching orders: {e}")
            
    return render_template('dashboard.html', user=session['user'], orders=orders, settings=settings)

@app.route('/add-order', methods=['POST'])
def add_order():
    if 'user' not in session: 
        return redirect('/login')
    if supabase:
        try:
            supabase.table("orders").insert({
                "customer_name": request.form.get('name'),
                "product_name": request.form.get('product'),
                "total_price": float(request.form.get('price', 0)) if request.form.get('price') else 0.0,
                "customer_phone": request.form.get('phone')
            }).execute()
        except Exception as e: 
            print(f"Error adding order: {e}")
    return redirect('/dashboard')

@app.route('/delete-order', methods=['POST'])
def delete_order():
    if 'user' not in session: 
        return redirect('/login')
    order_id = request.form.get('order_id')
    if supabase and order_id:
        try:
            supabase.table("orders").delete().eq("id", order_id).execute()
        except Exception as e: 
            print(f"Error deleting: {e}")
    return redirect('/dashboard')

@app.route('/edit-order', methods=['POST'])
def edit_order():
    if 'user' not in session: 
        return redirect('/login')
    order_id = request.form.get('order_id')
    if supabase and order_id:
        try:
            supabase.table("orders").update({
                "customer_name": request.form.get('name'),
                "product_name": request.form.get('product'),
                "total_price": float(request.form.get('price', 0)) if request.form.get('price') else 0.0,
                "customer_phone": request.form.get('phone')
            }).eq("id", order_id).execute()
        except Exception as e: 
            print(f"Error editing: {e}")
    return redirect('/dashboard')

@app.route('/update-info', methods=['POST'])
def update_info():
    if 'user' not in session: 
        return redirect('/login')
    if supabase:
        try:
            # نقوم بعمل الفحص والإنشاء أولاً للتأكد من وجود السطر
            get_or_create_settings()
            supabase.table("settings").update({
                "shop_name": request.form.get('shop_name'),
                "telegram_bot_token": request.form.get('bot_token'),
                "telegram_chat_id": request.form.get('chat_id')
            }).eq("id", 1).execute()
        except Exception as e:
            print(f"Error updating info: {e}")
    return redirect('/dashboard')

@app.route('/update-colors', methods=['POST'])
def update_colors():
    if 'user' not in session: 
        return redirect('/login')
    if supabase:
        try:
            get_or_create_settings()
            supabase.table("settings").update({
                "primary_color": request.form.get('primary_color'),
                "secondary_color": request.form.get('secondary_color')
            }).eq("id", 1).execute()
        except Exception as e:
            print(f"Error updating colors: {e}")
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
