from flask import Flask, request, render_template
from supabase import create_client
import os

app = Flask(__name__)

# إعداد Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# وظيفة الإضافة
@app.route('/add')
@app.route('/add')
def add_data():
    try:
        user_name = request.args.get('username', 'شيمو')
        data = supabase.table("users").insert({
            "username": user_name,
            "password": "123"
        }).execute()
        return "تمت الإضافة بنجاح!"
    except Exception as e:
        # إذا كان الخطأ بسبب تكرار الاسم، نخبر المستخدم بذلك بلطف
        if "23505" in str(e):
            return "هذا المستخدم موجود بالفعل في قاعدة البيانات."
        return f"حدث خطأ: {str(e)}"
