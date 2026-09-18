from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from supabase import create_client
from datetime import datetime
from functools import wraps
import os, time, requests, urllib.parse, base64, json
from google import genai 

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fallback_dev_key")
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB

supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- المعالجات والدوال المساعدة ---
@app.context_processor
def inject_currency():
    try:
        res = supabase.table('settings').select("currency").eq("company_code", session.get('company_code', '')).single().execute()
        return dict(currency=res.data.get('currency', 'DA') if res.data else 'DA')
    except:
        return dict(currency='DA')

def get_product_from_db(pid):
    try: return supabase.table("inventory").select("*").eq("id", pid).single().execute().data
    except: return None

def get_souhila_wilayas():
    try:
        res = supabase.table("algeria_wilayas").select("*").order("id").execute().data or []
        for w in res:
            w['home_price'], w['office_price'] = w.get('souhila_home_price', 0), w.get('souhila_office_price', 0)
        return res
    except: return []

def get_wilayas():
    try: return supabase.table("shipping_rates").select("*").order("id").execute().data or []
    except: return []

def send_telegram_alert(p_name, c_name, c_code=""):
    try:
        if c_code:
            s = supabase.table("settings").select("telegram_token, telegram_chat_id").eq("company_code", c_code).execute().data
            if s and s[0].get('telegram_token') and s[0].get('telegram_chat_id'):
                msg = f"🚨 نفاذ المخزون!\n🏪 المتجر: {c_name}\n📦 المنتج: {p_name}"
                requests.get(f"https://api.telegram.org/bot{s[0]['telegram_token']}/sendMessage?chat_id={s[0]['telegram_chat_id']}&text={requests.utils.quote(msg)}")
    except: pass

def send_telegram_by_token(token, chat_id, msg):
    try: return requests.get(f"https://api.telegram.org/bot{token}/sendMessage", params={"chat_id": chat_id, "text": msg}).status_code == 200
    except: return False

def send_order_alert(token, chat_id, msg, order_id):
    try:
        keyboard = {"inline_keyboard": [[{"text": "✅ تم", "callback_data": f"status_done_{order_id}"}, {"text": "❌ لم يتم", "callback_data": f"status_pending_{order_id}"}]]}
        return requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": msg, "reply_markup": keyboard}).status_code == 200
    except: return False

def get_products_by_shop(shop_name):
    try:
        decoded = urllib.parse.unquote(shop_name).strip()
        settings = supabase.table("settings").select("company_code").ilike("company_name", decoded).execute().data
        return supabase.table("inventory").select("*").eq("company_id_text", settings[0]['company_code']).execute().data if settings else []
    except: return []

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        return redirect(url_for('login')) if 'company_code' not in session else f(*args, **kwargs)
    return wrap

# --- المسارات العامة ---
@app.route('/favicon.ico')
def favicon(): return '', 204

@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/souhila')
def souhila_home():
    settings = {item['key']: item['value'] for item in (supabase.table('site_settings').select('*').execute().data or [])}
    courses = supabase.table('souhila_courses').select('*').execute().data or []
    return render_template('souhila.html', settings=settings, courses=courses)

@app.route('/souhila-checkout/<int:course_id>')
def souhila_checkout(course_id):
    rates = get_souhila_wilayas()
    course = supabase.table('souhila_courses').select('*').eq('id', course_id).single().execute().data
    settings = {item['key']: item['value'] for item in (supabase.table('site_settings').select('*').execute().data or [])}
    return render_template('souhila_checkout.html', rates=rates, course=course, settings=settings)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    msg = None
    if request.method == 'POST':
        f_type = request.form.get('form_type')
        try:
            if f_type == 'settings_update':
                supabase.table('site_settings').upsert([{'key': k, 'value': request.form.get(k)} for k in ['phone', 'whatsapp', 'email', 'map_url', 'telegram_token', 'telegram_chat_id']], on_conflict='key').execute()
                msg = "تم الحفظ بنجاح!"
            elif f_type == 'add_course':
                img_file = request.files.get('course_image')
                img_url = f"data:{img_file.content_type};base64,{base64.b64encode(img_file.read()).decode('utf-8')}" if img_file and img_file.filename else ""
                supabase.table('souhila_courses').insert({'title': request.form.get('course_title'), 'description': request.form.get('course_desc'), 'price': float(request.form.get('course_price') or 0), 'image': img_url, 'company_code': 'souhila'}).execute()
                msg = "تمت الإضافة!"
            elif f_type == 'delete_course':
                supabase.table('souhila_courses').delete().eq('id', request.form.get('course_id')).execute()
                msg = "تم الحذف!"
        except Exception as e: msg = f"خطأ: {e}"
        
    settings = {item['key']: item['value'] for item in (supabase.table('site_settings').select('*').execute().data or [])}
    return render_template('admin.html', settings=settings, courses=supabase.table('souhila_courses').select('*').execute().data or [], orders=supabase.table('orders_souhila').select('*').order('id', desc=True).execute().data or [], rates=get_souhila_wilayas(), msg=msg)

@app.route('/update_souhila_delivery_price', methods=['POST'])
def update_souhila_delivery_price():
    data = request.json if request.is_json else request.form
    try:
        supabase.table("algeria_wilayas").update({"souhila_office_price": float(data.get('office_price') or 0), "souhila_home_price": float(data.get('home_price') or 0)}).eq("id", int(data.get('id'))).execute()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/cart')
def cart_page(): return render_template('cart.html')

@app.route('/checkout_cart')
def checkout_cart_page(): return render_template('checkout.html', rates=get_wilayas(), is_cart=True)

@app.route('/checkout/<int:product_id>')
def checkout(product_id):
    product = get_product_from_db(product_id)
    if product and product.get('company_id_text'):
        s_res = supabase.table("settings").select("company_name").eq("company_code", product.get('company_id_text')).execute().data
        if s_res: session['current_shop_name'] = s_res[0].get('company_name')
    return render_template('checkout.html', product=product, rates=get_wilayas(), jordan_rates=supabase.table("jordan_rates").select("*").execute().data or [])

# --- معالجة الطلبات ---
@app.route('/submit-souhila-order', methods=['POST'])
def submit_souhila_order():
    f_name = f"{request.form.get('customer_name')} {request.form.get('customer_last_name', '')}".strip()
    phone, qty = request.form.get('phone'), int(request.form.get('quantity', 1))
    baladiya = request.form.get('baladiya') or request.form.get('baladia') or request.form.get('municipality') or request.form.get('city') or "غير محددة"
    
    cart = json.loads(request.form.get('cart_data', '[]')) if request.form.get('cart_data') else []
    p_id = request.form.get('product_id')
    if not cart and p_id: 
        prod = get_product_from_db(p_id)
        if prod: cart = [prod]
        
    total = sum(float(i.get('price', 0)) * int(i.get('quantity', 1)) for i in cart) + float(request.form.get('delivery_price', 0))
    region = request.form.get('wilaya')
    try:
        w_res = supabase.table("algeria_wilayas").select("wilaya_name").eq("id", region).single().execute().data
        if w_res: region = w_res.get('wilaya_name')
    except: pass
    
    p_names = ", ".join([f"{i.get('name', i.get('title'))} (x{i.get('quantity', 1)})" for i in cart])[:450]
    supabase.table("orders_souhila").insert({"customer_name": f_name, "customer_phone": phone, "product_name": p_names, "quantity": qty, "total_price": total, "status": "قيد الانتظار", "state": region, "baladiya": baladiya, "delivery_type": request.form.get('delivery_type'), "delivery_price": float(request.form.get('delivery_price', 0)), "product_id": cart[0].get('id') if cart else (int(p_id) if p_id else None), "color": request.form.get('selected_color', ''), "size": request.form.get('selected_size', '')}).execute()
    
    try:
        t_res = {item['key']: item['value'] for item in (supabase.table('site_settings').select('*').in_('key', ['telegram_token', 'telegram_chat_id']).execute().data or [])}
        if t_res.get('telegram_token') and t_res.get('telegram_chat_id'):
            send_telegram_by_token(t_res['telegram_token'], t_res['telegram_chat_id'], f"🛒 طلبية جديدة (سهيلة)!\n👤 الاسم: {f_name}\n📞 الهاتف: {phone}\n📦 المنتجات: {p_names}\n💰 المجموع: {total} دج")
    except: pass
    
    return """<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><title>نجاح</title></head><body style="text-align:center;padding-top:50px;font-family:Tahoma;"><div style="background:#fff;max-width:400px;margin:auto;padding:30px;border-radius:10px;box-shadow:0 0 10px rgba(0,0,0,0.1);"><p>شكراً لك، سيتم الاتصال بك قريباً.</p><a href="/souhila" style="background:#007bff;color:#fff;padding:10px 20px;text-decoration:none;border-radius:5px;display:inline-block;margin-top:20px;">العودة</a></div></body></html>"""

@app.route('/submit-order', methods=['GET', 'POST'])
def submit_order():
    if request.method == 'POST':
        f_name = f"{request.form.get('customer_name')} {request.form.get('customer_last_name', '')}".strip()
        phone, qty = request.form.get('phone'), int(request.form.get('quantity', 1))
        baladiya = request.form.get('baladiya') or request.form.get('baladia') or request.form.get('municipality') or request.form.get('city') or "غير محددة"
        d_type, d_price = request.form.get('delivery_type'), float(request.form.get('delivery_price', 0))
        o_type, t_num = request.form.get('order_type', 'delivery'), request.form.get('table_number', '')
        
        cart_items = []
        cart_raw = request.form.get('cart_data', '[]')
        if cart_raw and cart_raw != '[]':
            try:
                for item in json.loads(cart_raw):
                    cart_items.append({'id': item.get('id') or item.get('product_id'), 'name': str(item.get('name', 'منتج'))[:50], 'quantity': int(item.get('quantity', 1)), 'price': float(item.get('price', 0)), 'color': str(item.get('color', 'غير محدد'))[:20], 'size': str(item.get('size', 'غير محدد'))[:20]})
            except: cart_items = []
            
        p_single = request.form.get('product_id')
        if not cart_items and p_single:
            p_obj = get_product_from_db(p_single)
            if p_obj: cart_items = [{'id': p_obj.get('id'), 'name': str(p_obj.get('name'))[:50], 'quantity': qty, 'price': float(p_obj.get('price', 0)), 'color': request.form.get('selected_color', 'غير محدد')[:20], 'size': request.form.get('selected_size', 'غير محدد')[:20]}]
            
        p_summary = [f"📦 {i.get('name')} (الكمية: {i.get('quantity')}) | السعر: {float(i.get('price', 0)) * int(i.get('quantity', 1))} دج" for i in cart_items]
        grand_total = sum(float(i.get('price', 0)) * int(i.get('quantity', 1)) for i in cart_items) + d_price
        
        comp_code = next((get_product_from_db(i.get('id')).get('company_id_text') for i in cart_items if i.get('id') and get_product_from_db(i.get('id')) and get_product_from_db(i.get('id')).get('company_id_text')), "")
        if not comp_code and session.get('current_shop_name'):
            s_res = supabase.table("settings").select("company_code").ilike("company_name", session.get('current_shop_name').strip()).execute().data
            if s_res: comp_code = s_res[0]['company_code']
            
        region = request.form.get('wilaya', '')
        if request.form.get('country', 'algeria') == 'algeria' and region:
            try:
                w_res = supabase.table("shipping_rates").select("wilaya_name").eq("id", region).single().execute().data
                if w_res: region = w_res.get('wilaya_name')
            except: pass
            
        order_data = {"customer_name": f_name[:100], "customer_phone": phone[:30], "product_name": ", ".join([f"{i.get('name')} (x{i.get('quantity', 1)})" for i in cart_items])[:250], "quantity": qty, "total_price": grand_total, "status": "قيد الانتظار", "state": region[:50], "baladiya": baladiya[:50], "delivery_type": str(d_type)[:50], "delivery_price": d_price, "product_id": cart_items[0].get('id') if cart_items else (int(p_single) if p_single else None), "company_code": comp_code, "color": cart_items[0].get('color', 'غير محدد')[:20] if cart_items else 'غير محدد', "size": cart_items[0].get('size', 'غير محدد')[:20] if cart_items else 'غير محدد', "order_type": str(o_type)[:20], "table_number": str(t_num)[:20]}
        
        ins_id = None
        try:
            ins_res = supabase.table("orders").insert(order_data).execute().data
            if ins_res: ins_id = ins_res[0].get('id')
        except: pass
        
        for i in cart_items:
            try:
                if i.get('id'):
                    p_db = supabase.table("inventory").select("id, name, quantity").eq("id", i.get('id')).execute().data
                    if p_db:
                        new_q = max(0, int(p_db[0].get('quantity', 0)) - int(i.get('quantity', 1)))
                        supabase.table("inventory").update({"quantity": new_q}).eq("id", i.get('id')).execute()
                        if new_q <= 0: send_telegram_alert(p_db[0].get('name'), session.get('current_shop_name', ''), comp_code)
            except: pass
            
        if comp_code:
            try:
                set_res = supabase.table("settings").select("telegram_token, telegram_chat_id").eq("company_code", comp_code).execute().data
                if set_res and set_res[0].get('telegram_token') and set_res[0].get('telegram_chat_id'):
                    t_msg = f"🚨 **طلب جديد!**\n👤 الاسم: {f_name}\n📞 الهاتف: {phone}\n📌 نوع الطلب: {'🍽️ داخل المطعم (' + t_num + ')' if o_type == 'dine_in' else '🛵 توصيل'}\n🛍️ المنتجات:\n" + "\n".join(p_summary) + f"\n📍 العنوان: {region} - {baladiya}\n💰 المجموع: {grand_total} دج"
                    if ins_id: send_order_alert(set_res[0]['telegram_token'], set_res[0]['telegram_chat_id'], t_msg, ins_id)
                    else: send_telegram_by_token(set_res[0]['telegram_token'], set_res[0]['telegram_chat_id'], t_msg)
            except: pass
            
        return """<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><title>نجاح</title></head><body style="text-align:center;padding-top:50px;font-family:Tahoma;"><div style="background:#fff;max-width:400px;margin:auto;padding:30px;border-radius:10px;box-shadow:0 0 10px rgba(0,0,0,0.1);"><p>شكراً لثقتكم، تم تسجيل طلبكم بنجاح.</p><a href="/shop" style="background:#007bff;color:#fff;padding:10px 20px;text-decoration:none;border-radius:5px;display:inline-block;margin-top:20px;">العودة للمتجر</a></div></body></html>"""
    
    else:
        return redirect('/store2')

# --- لوحة التحكم والمصادقة ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        c_code = request.form.get('company_code')
        if supabase.table("settings").select("company_code").eq("company_code", c_code).execute().data:
            session['company_code'] = c_code
            return redirect(url_for('dashboard'))
        return "كود الشركة غير صحيح", 401
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        c_code, c_name = request.form.get('company_code'), request.form.get('company_name')
        if supabase.table("settings").select("company_code").eq("company_code", c_code).execute().data: return "الكود مستخدم مسبقاً", 400
        try:
            supabase.table("settings").insert({"company_code": c_code, "company_name": c_name}).execute()
            return "تم إنشاء الحساب بنجاح!"
        except Exception as e: return f"خطأ: {e}", 500
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('company_code', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard(): return render_template('dashboard.html')

@app.route('/stats')
@login_required
def stats():
    c_code = session.get('company_code')
    orders = supabase.table("orders").select("*").eq("company_code", c_code).execute().data or []
    days, months = {"السبت": 0, "الأحد": 0, "الاثنين": 0, "الثلاثاء": 0, "الأربعاء": 0, "الخميس": 0, "الجمعة": 0}, {"جانفي": 0, "فيفري": 0, "مارس": 0, "أفريل": 0, "ماي": 0, "جوان": 0, "جويلية": 0, "أوت": 0, "سبتمبر": 0, "أكتوبر": 0, "نوفمبر": 0, "ديسمبر": 0}
    d_map, m_map = {5: "السبت", 6: "الأحد", 0: "الاثنين", 1: "الثلاثاء", 2: "الأربعاء", 3: "الخميس", 4: "الجمعة"}, {1: "جانفي", 2: "فيفري", 3: "مارس", 4: "أفريل", 5: "ماي", 6: "جوان", 7: "جويلية", 8: "أوت", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"}
    yearly = {str(y): 0 for y in range(2026, max(datetime.now().year + 1, 2027))}
    
    total_rev = 0
    for o in orders:
        price = float(o.get("total_price") or 0)
        total_rev += price
        if o.get("created_at"):
            try:
                dt = datetime.fromisoformat(o.get("created_at").replace('Z', '+00:00'))
                if d_map.get(dt.weekday()) in days: days[d_map[dt.weekday()]] += price
                if m_map.get(dt.month) in months: months[m_map[dt.month]] += price
                if str(dt.year) in yearly: yearly[str(dt.year)] += price
            except: pass
            
    cleaned = [{"id": o.get("id"), "customer_name": str(o.get("customer_name") or ""), "total_price": float(o.get("total_price") or 0), "status": str(o.get("status") or ""), "created_at": str(o.get("created_at") or ""), "product_name": str(o.get("product_name") or "")} for o in orders]
    return render_template('stats.html', orders=cleaned, total_orders_count=len(orders), total_revenue=total_rev, total_expenses=0.0, daily=days, monthly=months, yearly=yearly)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    c_code = session.get('company_code')
    currencies = [("USD", "دولار أمريكي"), ("EUR", "يورو"), ("GBP", "جنيه إسترليني"), ("SAR", "ريال سعودي"), ("AED", "درهم إماراتي"), ("DZD", "دينار جزائري"), ("EGP", "جنيه مصري"), ("TND", "دينار تونسي"), ("MAD", "درهم مغربي"), ("TRY", "ليرة تركية")]
    if request.method == 'POST':
        try:
            supabase.table("settings").update({"company_name": request.form.get('shop_name'), "telegram_token": request.form.get('bot_token'), "telegram_chat_id": request.form.get('chat_id'), "instagram_url": request.form.get('instagram_link'), "currency": request.form.get('currency')}).eq("company_code", c_code).execute()
        except Exception as e: return f"خطأ: {e}", 500
        return redirect(url_for('settings'))
    res = supabase.table("settings").select("*").eq("company_code", c_code).execute().data
    return render_template('settings.html', settings=res[0] if res else {}, currencies=currencies)

@app.route('/shipping_settings', methods=['GET'])
@login_required
def shipping_settings(): return render_template('shipping_settings.html')

@app.route('/update_delivery_settings', methods=['POST'])
@login_required
def update_delivery_settings():
    supabase.table("company_settings").update({"delivery_office_price": request.json.get('office_price'), "delivery_home_price": request.json.get('home_price')}).eq("company_code", session.get('company_code')).execute()
    return jsonify({"status": "success"})

@app.route('/admin/jordan-shipping')
@login_required
def admin_jordan_shipping(): return render_template('admin_jordan.html', jordan_rates=supabase.table("jordan_rates").select("*").order("id").execute().data or [])

@app.route('/admin/update-jordan-rate/<int:id>', methods=['POST'])
@login_required
def update_jordan_rate(id):
    try:
        d = request.json if request.is_json else request.form
        supabase.table("jordan_rates").update({"home_price": float(d.get('home_price') or 0), "office_price": float(d.get('office_price') or 0)}).eq("id", id).execute()
        return jsonify({"status": "success"}) if request.is_json else redirect(url_for('orders'))
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500 if request.is_json else f"خطأ: {e}", 500

# --- إدارة المنتجات والمخزون ---
@app.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    c_code = session.get('company_code')
    if request.method == 'POST':
        file = request.files.get('product_image')
        img_str = f'data:image/jpeg;base64,{base64.b64encode(file.read()).decode("utf-8")}' if file and file.filename else ""
        try:
            supabase.table('inventory').insert({'name': request.form.get('name'), 'quantity': int(request.form.get('quantity', 0)), 'price': float(request.form.get('price', 0.0)), 'company_id_text': c_code, 'product-images': img_str, 'colors': request.form.get('colors', '').strip(), 'sizes': request.form.get('sizes', '').strip()}).execute()
            return redirect(url_for('products'))
        except Exception as e: return f"خطأ: {e}", 500
    return render_template('products.html', products=supabase.table("inventory").select("*").eq("company_id_text", c_code).execute().data or [])

@app.route('/inventory_management', methods=['GET', 'POST'])
@login_required
def inventory_management():
    c_code = session.get('company_code')
    if request.method == 'POST':
        file = request.files.get('product_image')
        up_data = {"quantity": int(request.form.get('quantity'))}
        if file and file.filename:
            path = f"{c_code}/{int(time.time())}_{file.filename}"
            supabase.storage.from_("products").upload(path, file.read(), {"content-type": file.content_type})
            up_data["product-images"] = supabase.storage.from_("products").get_public_url(path)
        try: supabase.table('inventory').update(up_data).eq("id", request.form.get('product_id')).eq("company_id_text", c_code).execute()
        except: pass
    res = supabase.table("inventory").select("*").eq("company_id_text", c_code).execute().data or []
    return render_template('inventory_management.html', inventory=res)

@app.route('/edit_product/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    c_code = session.get('company_code')
    prod = supabase.table("inventory").select("*").eq("id", id).eq("company_id_text", c_code).execute().data
    if not prod: return "غير موجود", 404
    if request.method == 'POST':
        supabase.table("inventory").update({"name": request.form.get('name'), "quantity": int(request.form.get('quantity')), "price": float(request.form.get('price')), "colors": request.form.get('colors', '').strip(), "sizes": request.form.get('sizes', '').strip()}).eq("id", id).execute()
        return redirect(url_for('products'))
    return render_template('edit_product.html', product=prod[0])

@app.route('/update_quantity/<int:product_id>', methods=['POST'])
@login_required
def update_quantity(product_id):
    prod = supabase.table("inventory").select("quantity").eq("id", product_id).eq("company_id_text", session.get('company_code')).single().execute().data
    if prod:
        amt = int(request.form.get('amount', 0))
        new_q = (prod.get('quantity', 0) + amt) if request.form.get('action_type') == 'add' else amt
        supabase.table("inventory").update({"quantity": new_q}).eq("id", product_id).execute()
    return redirect(url_for('products'))

@app.route('/delete_product/<int:id>', methods=['POST'])
@login_required
def delete_product(id):
    try: supabase.table("inventory").delete().eq("id", id).execute()
    except: pass
    return redirect(url_for('products'))

@app.route('/delete_order/<int:id>', methods=['POST'])
@login_required
def delete_order(id):
    supabase.table("orders").delete().eq("id", id).execute()
    return redirect(url_for('orders'))

@app.route('/update_status/<int:order_id>', methods=['POST'])
@login_required
def update_status(order_id):
    if request.form.get('status'): supabase.table("orders").update({"status": request.form.get('status')}).eq("id", order_id).execute()
    return redirect(url_for('orders'))

@app.route('/orders', methods=['GET', 'POST'])
@login_required
def orders():
    c_code = session.get('company_code')
    if request.method == 'POST':
        p_name, req_q = request.form.get('product_name'), int(request.form.get('quantity', 1))
        c_name, phone, state, d_type = request.form.get('customer_name'), request.form.get('customer_phone'), request.form.get('state'), request.form.get('delivery_type')
        d_price, base_price = float(request.form.get('delivery_price', 0)), float(request.form.get('price', 0))
        
        p_res = supabase.table("inventory").select("id, quantity").eq("name", p_name).eq("company_id_text", c_code).execute().data
        p_id = None
        if p_res:
            p_id = p_res[0]['id']
            supabase.table("inventory").update({"quantity": max(0, p_res[0]['quantity'] - req_q)}).eq("id", p_id).execute()
            
        ins_res = supabase.table("orders").insert({"customer_name": c_name, "customer_phone": phone, "product_name": p_name, "quantity": req_q, "total_price": base_price + d_price, "company_code": c_code, "status": "قيد الانتظار", "state": state, "delivery_type": d_type, "delivery_price": d_price, "product_id": p_id}).execute().data
        ins_id = ins_res[0].get('id') if ins_res else None
        
        s_res = supabase.table("settings").select("telegram_token, telegram_chat_id").eq("company_code", c_code).execute().data
        if s_res and s_res[0].get('telegram_token') and s_res[0].get('telegram_chat_id'):
            msg = f"🛒 طلبية من لوحة التحكم!\nالعميل: {c_name}\nالمنتج: {p_name}\nالكمية: {req_q}"
            if ins_id: send_order_alert(s_res[0]['telegram_token'], s_res[0]['telegram_chat_id'], msg, ins_id)
            else: send_telegram_by_token(s_res[0]['telegram_token'], s_res[0]['telegram_chat_id'], msg)
        return redirect(url_for('orders'))
        
    return render_template('orders_dashboard.html', orders=supabase.table("orders").select("*").eq("company_code", c_code).execute().data or [], wilayas=supabase.table("shipping_rates").select("*").order("id").execute().data or [], jordan_res=supabase.table("jordan_rates").select("*").order("id").execute().data or [])

# --- مسارات المتاجر الإضافية ---
@app.route('/shop', methods=['GET', 'POST'])
def shop():
    if request.method == 'POST' and request.form.get('company_name'): session['current_shop_name'] = request.form.get('company_name')
    shop_name = session.get('current_shop_name')
    return render_template('shop.html', products=get_products_by_shop(shop_name) if shop_name else [], current_company=shop_name)

@app.route('/clear_session')
def clear_session():
    session.pop('current_shop_name', None)
    return redirect(url_for('shop'))

@app.route('/store2', methods=['GET', 'POST'])
def store2():
    if request.method == 'POST' and request.form.get('company_name'): session['current_store2_name'] = request.form.get('company_name')
    shop_name = session.get('current_store2_name')
    return render_template('store2.html', products=get_products_by_shop(shop_name) if shop_name else [], current_company=shop_name)

@app.route('/clear_store2_session')
def clear_store2_session():
    session.pop('current_store2_name', None)
    return redirect(url_for('store2'))

@app.route('/store2_cart')
def store2_cart(): return render_template('store2_cart.html')

@app.route('/store2_checkout_page')
def store2_checkout_page(): return render_template('store2_checkout.html', rates=get_wilayas(), product=None)

@app.route('/store2_checkout/<int:product_id>')
def store2_checkout(product_id):
    product = get_product_from_db(product_id)
    if not product: return "غير موجود", 404
    return render_template('store2_checkout.html', product=product, rates=get_wilayas())

@app.route('/get_all_shipping_rates', methods=['GET'])
@login_required
def get_all_shipping_rates(): return jsonify(supabase.table("shipping_rates").select("*").order("id").execute().data)

@app.route('/update_delivery_price', methods=['POST'])
def update_delivery_price():
    data = request.json if request.is_json else request.form
    if not data.get('id'): return jsonify({"status": "error", "message": "ID missing"}), 400
    try:
        supabase.table("shipping_rates").update({"office_price": float(data.get('office_price') or 0), "home_price": float(data.get('home_price') or 0)}).eq("id", int(data.get('id'))).execute()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)