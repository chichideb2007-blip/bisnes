@app.route('/add')
def add_data():
    try:
        user_name = request.args.get('username', 'شيمو')
        # نقوم بإرسال قيم افتراضية لكل الأعمدة التي يطلبها الجدول
        data = supabase.table("users").insert({
            "username": user_name,
            "password": "123",        # قيمة افتراضية لكلمة السر
            "message": "لا يوجد"      # قيمة افتراضية للرسالة
        }).execute()
        return f"تمت الإضافة بنجاح للمستخدم: {user_name}"
    except Exception as e:
        return f"حدث خطأ: {str(e)}"
