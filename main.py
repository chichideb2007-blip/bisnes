# 1. إضافة دالة لجلب إعدادات المستخدم من Supabase
def get_user_bot_settings(user_id):
    try:
        response = supabase.table('settings').select('telegram_bot_token', 'telegram_chat_id').eq('user_id', user_id).single().execute()
        return response.data # يحتوي على التوكن والـ Chat ID الخاص بالعميل
    except:
        return None

# 2. تعديل دالة إضافة طلبية لتستخدم إعدادات العميل (اختياري: لإرسال تنبيه للبوت)
@app.route('/add-order', methods=['POST'])
def add_order():
    current_user = session.get('user_id')
    # جلب إعدادات هذا العميل فقط
    bot_settings = get_user_bot_settings(current_user)
    
    name = request.form.get('name')
    price = request.form.get('price')
    
    # حفظ الطلبية في قاعدة البيانات
    new_order = {
        "user_id": current_user, 
        "customer_name": name,
        "total_price": price
    }
    supabase.table('orders').insert(new_order).execute()
    
    # هنا يمكنك إضافة كود إرسال رسالة للبوت الخاص بالعميل باستخدام bot_settings['telegram_bot_token']
    
    return redirect('/dashboard')

# 3. تعديل دالة تحديث الإعدادات لكل عميل على حدة
@app.route('/update-info', methods=['POST'])
def update_info():
    current_user = session.get('user_id')
    updated_data = {
        "shop_name": request.form.get('shop_name'),
        "telegram_bot_token": request.form.get('bot_token'),
        "telegram_chat_id": request.form.get('chat_id')
    }
    # تحديث البيانات بناءً على الـ user_id الخاص بالمدير
    supabase.table('settings').update(updated_data).eq('user_id', current_user).execute()
    return redirect('/dashboard')
