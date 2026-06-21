from flask import Flask, request
import os
from supabase import create_client

app = Flask(__name__)

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/')
def home():
    return "السيرفر يعمل!"

@app.route('/add')
def add_data():
    try:
        # هنا نستخدم اسم العمود الصحيح الموجود في جدولك وهو 'username'
        user_name = request.args.get('username', 'ضيف')
        data = supabase.table("users").insert({"username": user_name}).execute()
        return f"تمت إضافة المستخدم: {user_name}"
    except Exception as e:
        return f"حدث خطأ: {str(e)}"

@app.route('/data')
def get_data():
    try:
        response = supabase.table("users").select("*").execute()
        return str(response.data)
    except Exception as e:
        return f"حدث خطأ: {str(e)}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
