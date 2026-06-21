@app.route('/add')
def add_data():
    try:
        user_name = request.args.get('username', 'شيمو')
        # نضيف قيماً افتراضية للأعمدة التي يطلبها الجدول إجبارياً
        data = supabase.table("users").insert({
            "username": user_name, 
            "message": "لا توجد رسالة", 
            "password": "123"
        }).execute()
        return f"تمت إضافة المستخدم: {user_name} بنجاح!"
    except Exception as e:
        return f"حدث خطأ: {str(e)}"
