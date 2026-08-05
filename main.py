from flask import Flask, render_template, request, redirect, url_for, session, jsonify, make_response
from supabase import create_client
from collections import defaultdict
from datetime import datetime
from functools import wraps
import os
import time
import requests
import urllib.parse
import base64
import json
from google import genai 
from google.genai import types 

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fallback_dev_key")

# إعداد Supabase و Gemini
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- المعالج التلقائي للعملة (مُحدث) ---
@app.context_processor
def inject_currency():
    company_code = session.get('company_code')
    if company_code:
        try:
            # نجلب العملة مرة واحدة للمتجر
            res = supabase.table('settings').select("currency").eq("company_code", company_code).single().execute()
            if res.data:
                return dict(currency=res.data.get('currency', ''))
        except:
            pass
    return dict(currency='DA') # العملة الافتراضية إذا لم توجد

# --- الدوال المساعدة ---

def get_product_from_db(product_id):
    res = supabase.table("inventory").select("*").eq("id", product_id).single().execute()
    return res.data if res.data else None

def get_wilayas_from_db():
    res = supabase.table("shipping_rates").select("*").order("id").execute()
    return res.data if res.data else []

def send_telegram_alert_by_token(token, chat_id, message):
    if not token or not chat_id:
        print("DEBUG: فشل إرسال التنبيه - التوكن أو Chat ID فارغ")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        params = {"chat_id": chat_id, "text": message}
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            print("DEBUG: تم إرسال التنبيه إلى تيلجرام بنجاح!")
            return True
        else:
            print(f"DEBUG: فشل الإرسال. الكود: {response.status_code}, الرد: {response.text}")
            return False
    except Exception as e:
        print(f"DEBUG: خطأ في الاتصال بتليجرام: {e}")
        return False

def send_order_alert(token, chat_id, message, order_id):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ تم التحضير", "callback_data": f"status_done_{order_id}"},
            {"text": "❌ لم يتم التحضير", "callback_data": f"status_pending_{order_id}"}
        ]]
    }
    params = {
        "chat_id": chat_id, 
        "text": message, 
        "reply_markup": keyboard
    }
    requests.post(url, json=params)

def get_products_by_shop_name(shop_name):
    try:
        shop_name_decoded = urllib.parse.unquote(shop_name).strip()
        print(f"DEBUG: ابحث عن متجر باسم: {shop_name_decoded}")
        
        settings = supabase.table("settings").select("company_code").ilike("company_name", shop_name_decoded).execute()
        
        if not settings.data:
            print("DEBUG: لم أجد متجراً بهذا الاسم")
            return []
        
        company_code = settings.data[0]['company_code']
        print(f"DEBUG: وجدت الكود: {company_code}")
        
        products = supabase.table("inventory").select("*").eq("company_id_text", company_code).execute()
        
        print(f"DEBUG: المنتجات التي وجدتها لـ {company_code} هي: {len(products.data)}")
        return products.data
    except Exception as e:
        print(f"DEBUG ERROR: {e}")
        return []

def get_delivery_price(wilaya, delivery_type):
    return 500

def refresh_instagram_token():
    res = supabase.table("settings").select("company_code, instagram_token").execute()
    for row in res.data:
        old_token = row.get('instagram_token')
        if old_token:
            url = f"https://graph.facebook.com/v20.0/oauth/access_token?grant_type=fb_exchange_token&client_id={os.environ.get('APP_ID')}&client_secret={os.environ.get('APP_SECRET')}&fb_exchange_token={old_token}"
            try:
                response = requests.get(url).json()
                new_token = response.get('access_token')
                if new_token:
                    supabase.table("settings").update({"instagram_token": new_token}).eq("company_code", row['company_code']).execute()
            except Exception as e:
                print(f"Token Refresh Error: {e}")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'company_code' not in session: return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- المسارات ---

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/checkout/<int:product_id>')
def checkout(product_id):
    response = supabase.table("shipping_rates").select("*").execute()
    rates = response.data 
    product = get_product_from_db(product_id)
    return render_template('checkout.html', product=product, rates=rates)

@app.route('/submit-order', methods=['POST'])
def submit_order():
    customer_name = request.form.get('customer_name')
    phone = request.form.get('phone')
    wilaya = request.form.get('wilaya') 
    baladiya = request.form.get('baladiya')
    delivery_type = request.form.get('delivery_type')
    delivery_price = float(request.form.get('delivery_price', 0))
    
    # التحقق مما إذا كانت السلة تحتوي على منتجات أو تم إرسال منتج مفرد
    cart_raw = request.form.get('cart_data', '')
    cart_data = []
    
    if cart_raw and cart_raw != '[]':
        try:
            cart_data = json.loads(cart_raw)
        except:
            cart_data = []
            
    # إذا لم تكن هناك سلة، نتحقق من وجود منتج مفرد مرسل بالطريقة التقليدية
    product_id = request.form.get('product_id')
    if not cart_data and product_id:
        single_product = get_product_from_db(product_id)
        if single_product:
            cart_data = [single_product]

    base_price = sum(float(item.get('price', 0)) for item in cart_data)
    total_price = base_price + delivery_price

    # جلب كود الشركة المرتبط بالمنتجات أو الجلسة الحالية
    company_code = ""
    if cart_data:
        first_item = cart_data[0]
        company_code = first_item.get('company_id_text') or first_item.get('company_code') or ""
    
    if not company_code and 'current_shop_name' in session:
        shop_name = session.get('current_shop_name')
        settings_res = supabase.table("settings").select("company_code").ilike("company_name", shop_name).execute()
        if settings_res.data:
            company_code = settings_res.data[0]['company_code']

    # تحويل معرف الولاية إلى اسمها الحقيقي إن أمكن ليكون واضحاً في الطلبات
    wilaya_name = wilaya
    try:
        w_res = supabase.table("shipping_rates").select("wilaya_name").eq("id", wilaya).single().execute()
        if w_res.data and w_res.data.get('wilaya_name'):
            wilaya_name = w_res.data.get('wilaya_name')
    except:
        pass

    # 1. حفظ الطلب في جدول orders
    order_data = {
        "customer_name": customer_name,
        "customer_phone": phone,
        "product_name": ", ".join([str(item.get('name', 'منتج')) for item in cart_data]), 
        "quantity": len(cart_data) if len(cart_data) > 0 else 1,
        "total_price": total_price,
        "company_code": company_code,
        "status": "قيد الانتظار",
        "state": wilaya_name,
        "baladiya": baladiya,
        "delivery_type": delivery_type,
        "delivery_price": delivery_price
    }
    
    try:
        supabase.table("orders").insert(order_data).execute()
    except Exception as e:
        print(f"Error inserting order: {e}")

    # 2. خصم الكميات تلقائياً من جدول المخزون (inventory) الخاص بالشركة
    for item in cart_data:
        p_id = item.get('id')
        if p_id:
            try:
                query = supabase.table("inventory").select("quantity, name").eq("id", p_id)
                if company_code:
                    query = query.eq("company_id_text", company_code)
                
                prod_res = query.single().execute()
                
                if prod_res.data:
                    current_qty = prod_res.data.get('quantity', 0)
                    new_qty = max(0, current_qty - 1)  # خصم قطعة واحدة لكل منتج
                    
                    update_query = supabase.table("inventory").update({"quantity": new_qty}).eq("id", p_id)
                    if company_code:
                        update_query = update_query.eq("company_id_text", company_code)
                    update_query.execute()
            except Exception as ex:
                print(f"Error updating inventory for product {p_id}: {ex}")

    # 3. إرسال تنبيه تيليجرام لمدير الشركة
    if company_code:
        res_settings = supabase.table("settings").select("telegram_token, telegram_chat_id").eq("company_code", company_code).execute()
        if res_settings.data:
            s = res_settings.data[0]
            token, chat_id = s.get('telegram_token'), s.get('telegram_chat_id')
            product_names_str = ", ".join([str(item.get('name', 'منتج')) for item in cart_data])
            if token and chat_id:
                msg = (f"🛒 طلبية جديدة من المتجر!\n👤 الاسم: {customer_name}\n📞 الهاتف: {phone}\n📦 المنتجات: {product_names_str}\n📍 الولاية: {wilaya_name}\n🏘️ البلدية: {baladiya}\n🚚 التوصيل: {delivery_type} ({delivery_price} دج)\n💰 المجموع الكلي: {total_price} دج")
                send_telegram_alert_by_token(token, chat_id, msg)

    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>تم الطلب بنجاح</title>
        <style>
            body {{ font-family: Tahoma, sans-serif; background-color: #f4f7f6; text-align: center; padding-top: 50px; margin: 0; }}
            .card {{ background: white; max-width: 400px; margin: auto; padding: 30px; border-radius: 10px; box-shadow: 0px 4px 10px rgba(0,0,0,0.1); }}
            h2 {{ color: #28a745; }}
            p {{ color: #555; font-size: 16px; }}
            .btn {{ display: inline-block; margin-top: 20px; background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
            .btn:hover {{ background: #0056b3; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>🎉 تم تأكيد طلبك بنجاح!</h2>
            <p>شكراً لثقتكم بنا، سيتم الاتصال بكم قريباً لتأكيد الطلب.</p>
            <a href="/shop" class="btn">🔙 العودة إلى المتجر</a>
        </div>
    </body>
    </html>
    """

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        company_code = request.form.get('company_code')
        res = supabase.table("settings").select("company_code").eq("company_code", company_code).execute()
        if res.data:
            session['company_code'] = company_code
            return redirect(url_for('dashboard'))
        else:
            return "كود الشركة غير صحيح، يرجى التأكد منه.", 401
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        company_code = request.form.get('company_code')
        company_name = request.form.get('company_name')
        res = supabase.table("settings").select("company_code").eq("company_code", company_code).execute()
        if res.data:
            return "هذا الكود مستخدم بالفعل، يرجى اختيار كود آخر!", 400
        try:
            supabase.table("settings").insert({"company_code": company_code, "company_name": company_name}).execute()
            return "تم إنشاء الحساب بنجاح!"
        except Exception as e:
            return f"حدث خطأ: {e}", 500
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('company_code', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/check_orphaned_products')
@login_required
def check_orphaned_products():
    try:
        res = supabase.rpc("get_orphaned_products").execute()
        return jsonify({"orphaned_products": res.data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stats')
@login_required
def stats():
    company_code = session.get('company_code')
    try:
        res = supabase.table("orders").select("*").eq("company_code", company_code).execute()
        orders = res.data or []
    except Exception as e:
        orders = []

    cleaned_orders = []
    for order in orders:
        cleaned_order = {
            "id": order.get("id"),
            "customer_name": str(order.get("customer_name") or ""),
            "total_price": float(order.get("total_price") or 0),
            "status": str(order.get("status") or ""),
            "created_at": str(order.get("created_at") or ""),
            "product_name": str(order.get("product_name") or "")
        }
        cleaned_orders.append(cleaned_order)

    return render_template('stats.html', orders=cleaned_orders, daily=[])

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    company_code = session.get('company_code')
    currencies = [
        ("USD", "دولار أمريكي"), ("EUR", "يورو"), ("GBP", "جنيه إسترليني"), ("JPY", "ين ياباني"),
        ("SAR", "ريال سعودي"), ("AED", "درهم إماراتي"), ("DZD", "دينار جزائري"), ("EGP", "جنيه مصري"),
        ("KWD", "دينار كويتي"), ("QAR", "ريال قطري"), ("BHD", "دينار بحريني"), ("OMR", "ريال عماني"),
        ("JOD", "دينار أردني"), ("LBP", "ليرة لبنانية"), ("LYD", "دينار ليبي"), ("MAD", "درهم مغربي"),
        ("TND", "دينار تونسي"), ("IQD", "دينار عراقي"), ("SYP", "ليرة سورية"), ("YER", "ريال يمني"),
        ("TRY", "ليرة تركية"), ("AUD", "دولار أسترالي"), ("CAD", "دولار كندي"), ("CHF", "فرنك سويسري"),
        ("CNY", "يوان صيني"), ("INR", "روبية هندية"), ("RUB", "روبل روسي"), ("SGD", "دولار سنغافوري"),
        ("SDG", "جنيه سوداني"), ("MRU", "أوقية موريتانية"), ("SOS", "شلن صومالي"), ("KMF", "فرنك جزر القمر"),
        ("DJF", "فرنك جيبوتي"), ("BND", "دولار بروناي"), ("KRW", "وون كوري جنوبي"), ("MXN", "بيزو مكسيكي")
    ]
    
    if request.method == 'POST':
        data = {
            "company_name": request.form.get('shop_name'),
            "telegram_token": request.form.get('bot_token'),
            "telegram_chat_id": request.form.get('chat_id'),
            "instagram_url": request.form.get('instagram_link'),
            "currency": request.form.get('currency') 
        }
        try:
            supabase.table("settings").update(data).eq("company_code", company_code).execute()
        except Exception as e:
            return f"حدث خطأ أثناء الحفظ: {str(e)}", 500
        return redirect(url_for('settings'))
    
    res = supabase.table("settings").select("*").eq("company_code", company_code).execute()
    settings_data = res.data[0] if res.data else {}
    return render_template('settings.html', settings=settings_data, currencies=currencies)

@app.route('/shipping_settings', methods=['GET'])
@login_required
def shipping_settings():
    return render_template('shipping_settings.html')

@app.route('/get_delivery_prices', methods=['GET'])
@login_required
def get_delivery_prices():
    company_code = session.get('company_code')
    data = supabase.table("delivery_prices").select("*").eq("company_code", company_code).execute()
    return jsonify(data.data)

@app.route('/update_delivery_price', methods=['POST'])
@login_required
def update_delivery_price():
    data = request.json
    row_id = data.get('id')
    new_office = data.get('office_price')
    new_home = data.get('home_price')
    
    try:
        supabase.table("shipping_rates").update({
            "office_price": new_office,
            "home_price": new_home
        }).eq("id", row_id).execute()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_shipping_rates')
def get_shipping_rates():
    company_code = request.args.get('company_code')
    delivery_type = request.args.get('type') 
    
    try:
        res = supabase.table("delivery_prices") \
            .select("home_price, office_price") \
            .eq("company_code", company_code) \
            .single().execute()
        if res.data:
            price = res.data.get('home_price') if delivery_type == 'home' else res.data.get('office_price')
            return jsonify({"price": float(price or 0)})
    except Exception as e:
        pass
    return jsonify({"price": 0})

@app.route('/get_all_shipping_rates', methods=['GET'])
@login_required
def get_all_shipping_rates():
    res = supabase.table("shipping_rates").select("*").order("id").execute()
    return jsonify(res.data)

@app.route('/get_delivery_settings', methods=['GET'])
@login_required
def get_delivery_settings():
    company_code = session.get('company_code')
    data = supabase.table("company_settings").select("*").eq("company_code", company_code).single().execute()
    return jsonify(data.data)

@app.route('/update_delivery_settings', methods=['POST'])
@login_required
def update_delivery_settings():
    data = request.json
    company_code = session.get('company_code')
    supabase.table("company_settings").update({
        "delivery_office_price": data.get('office_price'),
        "delivery_home_price": data.get('home_price')
    }).eq("company_code", company_code).execute()
    return jsonify({"status": "success"})

@app.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    company_code = session.get('company_code')
    
    if request.method == 'POST':
        file = request.files.get('product_image')
        encoded_string = ""
        if file and file.filename != '':
            encoded_string = f'data:image/jpeg;base64,{base64.b64encode(file.read()).decode("utf-8")}'

        data = {
            'name': request.form.get('name'),
            'quantity': int(request.form.get('quantity', 0)),
            'price': float(request.form.get('price', 0.0)),
            'company_id_text': company_code,
            'product-images': encoded_string
        }
        try:
            supabase.table('inventory').insert(data).execute()
            return redirect(url_for('products'))
        except Exception as e:
            return f"خطأ في قاعدة البيانات: {str(e)}", 500

    res = supabase.table("inventory").select("*").eq("company_id_text", company_code).execute()
    return render_template('products.html', products=res.data or [])


@app.route('/inventory_management', methods=['GET', 'POST'])
@login_required
def inventory_management():
    company_code = session.get('company_code')
    
    if request.method == 'POST':
        product_id = request.form.get('product_id')
        new_quantity = request.form.get('quantity')
        file = request.files.get('product_image')
        
        update_data = {"quantity": int(new_quantity)}
        
        if file and file.filename != '':
            filename = f"{company_code}/{int(time.time())}_{file.filename}"
            supabase.storage.from_("products").upload(
                path=filename,
                file=file.read(),
                file_options={"content-type": file.content_type}
            )
            public_url = supabase.storage.from_("products").get_public_url(filename)
            update_data["product-images"] = public_url
        
        try:
            supabase.table('inventory').update(update_data).eq("id", product_id).eq("company_id_text", company_code).execute()
        except Exception as e:
            print(f"DEBUG: خطأ في تحديث المخزون: {e}")
            
    try:
        res = supabase.table("inventory").select("*").eq("company_id_text", company_code).execute()
        inventory_data = res.data or []
    except Exception as e:
        inventory_data = []
        
    return render_template('inventory_management.html', inventory=inventory_data)

@app.route('/edit_product/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    company_code = session.get('company_code')
    res = supabase.table("inventory").select("*").eq("id", id).eq("company_id_text", company_code).execute()
    product = res.data[0] if res.data else None
    
    if not product:
        return "المنتج غير موجود", 404

    if request.method == 'POST':
        new_name = request.form.get('name')
        new_quantity = request.form.get('quantity')
        new_price = request.form.get('price')
        
        supabase.table("inventory").update({
            "name": new_name,
            "quantity": int(new_quantity),
            "price": float(new_price)
        }).eq("id", id).execute()
        
        return redirect(url_for('products'))
        
    return render_template('edit_product.html', product=product)

@app.route('/delete_product/<int:id>', methods=['POST'])
@login_required
def delete_product(id):
    try: supabase.table("inventory").delete().eq("id", id).execute()
    except Exception as e: print(f"Delete Error: {e}")
    return redirect(url_for('products'))

@app.route('/delete_order/<int:id>', methods=['POST'])
@login_required
def delete_order(id):
    supabase.table("orders").delete().eq("id", id).execute()
    return redirect(url_for('orders'))

@app.route('/update_status/<int:order_id>', methods=['POST'])
@login_required
def update_status(order_id):
    new_status = request.form.get('status')
    if new_status:
        supabase.table("orders").update({"status": new_status}).eq("id", order_id).execute()
    return redirect(url_for('orders'))

@app.route('/orders', methods=['GET', 'POST'])
@login_required
def orders():
    company_code = session.get('company_code')
    wilayas_res = supabase.table("shipping_rates").select("*").order("id").execute()
    
    if request.method == 'POST':
        product_name = request.form.get('product_name')
        requested_qty = int(request.form.get('quantity', 0))
        customer_name = request.form.get('customer_name')
        
        state = request.form.get('state')
        delivery_type = request.form.get('delivery_type')
        delivery_price = float(request.form.get('delivery_price', 0.0))
        
        base_price = float(request.form.get('price', 0.0))
        total_price = base_price + delivery_price
        
        data = {
            "customer_name": customer_name,
            "customer_phone": request.form.get('customer_phone'), 
            "product_name": product_name,
            "quantity": requested_qty, 
            "total_price": total_price,
            "company_code": company_code,
            "status": "قيد الانتظار",
            "state": state,
            "delivery_type": delivery_type,
            "delivery_price": delivery_price
        }
        supabase.table("orders").insert(data).execute()
        
        res_settings = supabase.table("settings").select("telegram_token, telegram_chat_id").eq("company_code", company_code).execute()
        settings_info = res_settings.data[0] if res_settings.data else {}
        token = settings_info.get('telegram_token')
        chat_id = settings_info.get('telegram_chat_id')
        
        if token and chat_id:
            msg = f"🛒 طلبية جديدة!\nالعميل: {customer_name}\nالمنتج: {product_name}\nالكمية: {requested_qty}\nالولاية: {state}\nالتوصيل: {delivery_type} ({delivery_price})"
            send_telegram_alert_by_token(token, chat_id, msg)
            
            products_res = supabase.table("inventory").select("id, quantity").eq("name", product_name).eq("company_id_text", company_code).execute()
            
            if products_res.data:
                product = products_res.data[0]
                current_qty = product['quantity']
                new_qty = max(0, current_qty - requested_qty)
                supabase.table("inventory").update({"quantity": new_qty}).eq("id", product['id']).execute()
                
                if new_qty == 0:
                    send_telegram_alert_by_token(token, chat_id, f"❌ تنبيه هام!\nالمنتج '{product_name}' قد نفذ تماماً من المخزون.")
                elif new_qty <= 5:
                    send_telegram_alert_by_token(token, chat_id, f"⚠️ تنبيه مخزون!\nالمنتج '{product_name}' أوشك على النفاذ، المتبقي حالياً: {new_qty}")
            
        return redirect(url_for('orders'))

    res = supabase.table("orders").select("*").eq("company_code", company_code).execute()
    return render_template('orders_dashboard.html', orders=res.data or [], wilayas=wilayas_res.data)

@app.route('/shop', methods=['GET', 'POST'])
def shop():
    if request.method == 'POST' and 'company_name' in request.form:
        session['current_shop_name'] = request.form.get('company_name')
        return redirect(url_for('shop'))

    elif request.method == 'POST' and 'product_id' in request.form:
        product_id = request.form.get('product_id')
        customer_name = request.form.get('customer_name')
        customer_phone = request.form.get('phone')
        wilaya = request.form.get('wilaya')
        baladiya = request.form.get('baladiya')
        delivery_type = request.form.get('delivery_type')
        
        delivery_price = 0
        try:
            shipping_res = supabase.table("shipping_rates").select("*").eq("id", wilaya).single().execute()
            if shipping_res.data:
                delivery_price = float(shipping_res.data.get('home_price') if delivery_type == 'home' else shipping_res.data.get('office_price') or 0)
        except:
            delivery_price = 0

        if not product_id:
            return "خطأ: معرف المنتج مفقود", 400

        product_res = supabase.table("inventory").select("*").eq("id", product_id).single().execute()
        product = product_res.data
        
        if not product:
            return "المنتج غير موجود!", 404

        company_code = product.get('company_id_text')

        if not company_code and 'current_shop_name' in session:
            shop_name = session.get('current_shop_name')
            settings_res = supabase.table("settings").select("company_code").ilike("company_name", shop_name).execute()
            if settings_res.data:
                company_code = settings_res.data[0]['company_code']

        total_price = float(product['price']) + delivery_price

        wilaya_name = wilaya
        try:
            w_res = supabase.table("shipping_rates").select("wilaya_name").eq("id", wilaya).single().execute()
            if w_res.data:
                wilaya_name = w_res.data.get('wilaya_name')
        except:
            pass

        order_data = {
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "product_name": product['name'],
            "quantity": 1,
            "total_price": total_price,
            "delivery_price": delivery_price,
            "status": "قيد الانتظار",
            "company_code": company_code,
            "state": wilaya_name,
            "baladiya": baladiya,
            "delivery_type": delivery_type
        }
        
        supabase.table("orders").insert(order_data).execute()

        if company_code:
            res_settings = supabase.table("settings").select("telegram_token, telegram_chat_id").eq("company_code", company_code).execute()
            if res_settings.data:
                s = res_settings.data[0]
                token, chat_id = s.get('telegram_token'), s.get('telegram_chat_id')
                if token and chat_id:
                    msg = (f"⚡ طلب شراء جديد من المتجر!\n👤 الزبون: {customer_name}\n📞 الهاتف: {customer_phone}\n📦 المنتج: {product['name']}\n💰 الإجمالي: {total_price} دج\n📍 الولاية: {wilaya_name}\n🏘️ البلدية: {baladiya}\n🚚 التوصيل: {delivery_type}")
                    send_telegram_alert_by_token(token, chat_id, msg)

        current_qty = product.get('quantity', 0)
        new_qty = max(0, current_qty - 1)
        
        update_query = supabase.table("inventory").update({"quantity": new_qty}).eq("id", product_id)
        if company_code:
            update_query = update_query.eq("company_id_text", company_code)
        update_query.execute()

        return "تمت عملية الشراء بنجاح وسيتم الاتصال بك قريباً!"

    shop_name = session.get('current_shop_name')
    products = []
    if shop_name:
        products = get_products_by_shop_name(shop_name)
    
    return render_template('shop.html', products=products, current_company=shop_name)

@app.route('/clear_session')
def clear_session():
    session.pop('current_shop_name', None)
    return redirect(url_for('shop'))

if __name__ =='__main__':
    app.run(debug=True)