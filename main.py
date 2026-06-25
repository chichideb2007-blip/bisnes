import os
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
from supabase import create_client, Client

app = Flask(__name__)
# مفتاح الجلسة لتأمين بيانات المدير
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "shimo-saas-secure-2026")

# الذاكرة الاحتياطية لتأمين الحفظ الفوري للمديرين داخل السيرفر في حال تشنج الاتصال
if not hasattr(app, 'global_orders'):
    app.global_orders = []

# جلب بيانات الاتصال بـ Supabase من متغيرات البيئة على Render
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY")

supabase = None
if SUPABASE_URL and SUPABASE_KEY and "your-supabase" not in SUPABASE_URL:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Supabase init error: {e}")

def get_user_settings(user_id):
    """جلب إعدادات الألوان واسم المتجر للمدير الحالي"""
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
            print(f"Fallback to local memory: {e}")
            orders = [o for o in app.global_orders if o.get('user_id') == current_user_id]
    else:
        orders = [o for o in app.global_orders if o.get('user_id') == current_user_id]

    # جلب السنة الحالية تلقائياً من النظام (ديناميكي) لتبدأ من 2026 وتتغير تلقائياً كل عام
    now = datetime.now()
    current_year = now.year 

    daily_total = 0.0
    monthly_total = 0.0
    yearly_total = 0.0

    # مصفوفات لتجهيز بيانات المنحنيات الشاملة (7 أيام للأسبوع و12 شهراً للأشعر)
    weekly_data = [0.0] * 7  # مرتبة: سبت، أحد، اثنين، ثلاثاء، أربعاء، خميس، جمعة
    monthly_data = [0.0] * 12 # 12 شهر كاملة من جانفي إلى ديسمبر

    for o in orders:
        try:
            price = float(o.get('total_price', 0) or 0)
            created_at_str = o.get('created_at', '')
            if created_at_str:
                # تنظيف صيغة الوقت القادمة من قاعدة البيانات لقرائتها برمجياً
                clean_date_str = created_at_str.split('.')[0].replace('Z', '').replace('T', ' ')
                order_date = datetime.strptime(clean_date_str, "%Y-%m-%d %H:%M:%S")
                
                # حساب الإحصائيات للمنحنيات بناءً على السنة الحالية تلقائياً
                if order_date.year == current_year:
                    yearly_total += price
                    
                    # توزيع الأرباح على مصفوفة الأشهر الاثني عشر بدقة
                    monthly_data[order_date.month - 1] += price
                    
                    if order_date.month == now.month:
                        monthly_total += price
                        
                    # تعديل ترتيب أيام الأسبوع في بايثون لتبدأ الحسابات من يوم السبت كبداية للأسبوع
                    day_idx = (order_date.weekday() + 2) % 7 
                    weekly_data[day_idx] += price
                    
                    if order_date.date() == now.date():
                        daily_total += price
        except Exception as ex:
            print(f"Date parsing error: {ex}")

    return render_template(
        'dashboard.html', 
        orders=orders, 
        settings=settings,
        daily_total=round(daily_total, 2),
        monthly_total=round(monthly_total, 2),
        yearly_total=round(yearly_total, 2),
        weekly_data=weekly_data,
        monthly_data=monthly_data,
        current_year=current_year
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

    # الحفظ في الذاكرة المحلية الفورية أولاً لسرعة التحديث أمام المدير
    app.global_orders.insert(0, new_order)

    # دفع البيانات متزامنة إلى سوبابايس
    if supabase:
        try:
            supabase.table("orders").insert(new_order).execute()
        except Exception as e:
            print(f"Database insertion error: {e}")

    return redirect(url_for('dashboard'))

# 🛠️ دالة إصلاح تغيير الألوان اللانهائي والمضمون 100% لتجاوز قفل الجدول
@app.route('/update-colors', methods=['POST'])
def update_colors():
    if 'user_id' not in session:
        return redirect(url_for('dashboard'))
    current_user_id = session['user_id']
    p_color = request.form.get('primary_color')
    s_color = request.form.get('secondary_color')
    
    color_data = {
        "user_id": current_user_id,
        "primary_color": p_color,
        "secondary_color": s_color
    }
    
    if supabase:
        try:
            # التحقق الفوري لو كان للمستخدم سجل إعدادات سابق في سوبابايس
            check_res = supabase.table("settings").select("id").eq("user_id", current_user_id).maybe_single().execute()
            if check_res and check_res.data:
                # إذا وجده، يقوم بعمل تحديث (Update) مباشر وآمن دون حذف، مما يكسر التجميد والقفل تماماً
                supabase.table("settings").update({"primary_color": p_color, "secondary_color": s_color}).eq("user_id", current_user_id).execute()
                print("✅ تم تحديث ألوان المدير بنجاح واختراق تجميد البيانات!")
            else:
                # إذا كانت هذه أول مرة للمدير، يقوم بعملية الإدخال الجديدة (Insert)
                supabase.table("settings").insert(color_data).execute()
                print("✅ تم حفظ الألوان الجديدة للمرة الأولى بنجاح!")
        except Exception as e:
            print(f"❌ فشل تحديث الألوان في قاعدة البيانات: {e}")
            
    return redirect(url_for('dashboard'))

@app.route('/delete-order', methods=['POST'])
def delete_order():
    if 'user_id' not in session:
        return redirect(url_for('dashboard'))
    order_id = request.form.get('order_id')
    current_user_id = session['user_id']
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
        "shop_name": request.form.get('shop_name'),
        "telegram_bot_token": request.form.get('bot_token'),
        "telegram_chat_id": request.form.get('chat_id')
    }
    if supabase:
        try:
            check_res = supabase.table("settings").select("id").eq("user_id", current_user_id).maybe_single().execute()
            if check_res and check_res.data:
                supabase.table("settings").update(updated_data).eq("user_id", current_user_id).execute()
            else:
                updated_data["user_id"] = current_user_id
                supabase.table("settings").insert(updated_data).execute()
        except Exception as e:
            print(f"Error updating info: {e}")
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
