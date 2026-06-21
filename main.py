@app.route('/add')
def add_data():
    try:
        user_name = request.args.get('username', 'شيمو')
        # الآن نرسل فقط 'username' لأن بقية الأعمدة تقبل Null
        data = supabase.table("users").insert({"username": user_name}).execute()
        return "تمت إضافة المستخدم بنجاح!"
    except Exception as e:
        return f"حدث خطأ: {str(e)}"
