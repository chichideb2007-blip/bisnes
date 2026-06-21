from flask import Flask, request
from supabase import create_client
import os

app = Flask(__name__)

# إعداد Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# هذه الوصفة للإضافة
@app.route('/add')
@app.route('/add')
def add_data():
    try:
        user_name = request.args.get('username', 'شيمو')
        # سنحذف company_id و role لأنها تسبب المشكلة
        data = supabase.table("users").insert({
            "username": user_name,
            "password": "123"
        }).execute()
        return "تمت الإضافة بنجاح!"
    except Exception as e:
        return f"حدث خطأ: {str(e)}"
