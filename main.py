@app.route('/add')
def add_data():
    try:
        user_name = request.args.get('username', 'شيمو')
        # سنرسل كل شيء يطلبه الجدول لكي لا يعترض
        data = supabase.table("users").insert({
            "username": user_name,
            "password": "123",       # قيمة افتراضية
            "company_id": 1,         # قيمة افتراضية
            "role": "user"           # قيمة افتراضية (إذا كان هذا العمود موجوداً)
        }).execute()
        return "تمت الإضافة بنجاح!"
    except Exception as e:
        return f"حدث خطأ: {str(e)}"
