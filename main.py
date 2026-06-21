@app.route('/add')
def add_data():
    try:
        user_name = request.args.get('username', 'شيمو')
        # نقوم بإرسال قيمة للعمود الذي يشتكي منه (company_id)
        data = supabase.table("users").insert({
            "username": user_name,
            "company_id": 1  # هذه القيمة ستحل المشكلة
        }).execute()
        return "تمت الإضافة بنجاح للمستخدم: " + user_name
    except Exception as e:
        return f"حدث خطأ: {str(e)}"
