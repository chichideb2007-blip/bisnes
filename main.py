from flask import Flask, request
from supabase import create_client
import os

app = Flask(__name__)

# إعداد Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# وظيفة الإضافة
@app.route('/add')
def add_data():
    try:
        user_name = request.args.get('username', 'شيمو')
        # سنحاول الإضافة بدون company_id
        data = supabase.table("users").insert({
            "username": user_name,
            "password": "123"
        }).execute()
        return "تمت الإضافة بنجاح!"
    except Exception as e:
        return f"حدث خطأ: {str(e)}"

# وظيفة العرض
@app.route('/users')
def get_users():
    try:
        response = supabase.table("users").select("*").execute()
        return str(response.data)
    except Exception as e:
        return f"حدث خطأ: {str(e)}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
