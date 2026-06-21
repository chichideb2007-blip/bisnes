@app.route('/add')
def add_data():
    try:
        user_name = request.args.get('username', 'شيمو')
        # هنا سنرسل قيم فارغة لكل الأعمدة التي يطلبها الجدول
        data = supabase.table("users").insert({
            "username": user_name,
            "password": " ",    # مسافة فارغة
            "message": " "      # مسافة فارغة
        }).execute()
        return "تمت الإضافة بنجاح!"
    except Exception as e:
        return f"حدث خطأ: {str(e)}"
