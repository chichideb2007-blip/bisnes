@app.route('/add')
def add_data():
    try:
        user_name = request.args.get('username', 'شيمو')
        # سنحاول الإضافة ببيانات شاملة لكل الأعمدة المحتملة
        data = supabase.table("users").insert({
            "username": user_name,
            "password": " ", 
            "message": " ",
            "company_id": 1 # إذا كان هناك عمود لهذا الاسم
        }).execute()
        return "تمت الإضافة بنجاح!"
    except Exception as e:
        # هذا السطر سيخبرنا بالضبط ما هو العمود المتبقي الذي يسبب المشكلة
        error_msg = str(e)
        return f"الخطأ هو: {error_msg}"
