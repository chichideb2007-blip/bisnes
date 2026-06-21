@app.route('/add')
def add_data():
    try:
        user_name = request.args.get('username', 'شيمو')
        # الآن بما أن الأعمدة تقبل Null، يمكننا إرسال username فقط
        data = supabase.table("users").insert({"username": user_name}).execute()
        return "تمت إضافة المستخدم بنجاح!"
    except Exception as e:
        return f"حدث خطأ: {str(e)}"
