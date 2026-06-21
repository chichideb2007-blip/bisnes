@app.route('/users')
def get_users():
    try:
        # جلب كل البيانات من جدول users
        response = supabase.table("users").select("*").execute()
        return str(response.data)
    except Exception as e:
        return f"حدث خطأ أثناء جلب البيانات: {str(e)}"
