from flask import Flask, request
import os
from supabase import create_client

app = Flask(__name__)

# إعداد الاتصال باستخدام المتغيرات الموجودة في Render
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/')
def home():
    return "السيرفر يعمل!"

@app.route('/add')
def add_data():
    try:
        name = request.args.get('name', 'شيماء')
        message = request.args.get('message', 'مرحباً')
        # تأكدي أن اسم الجدول في Supabase هو 'users' تماماً
        data = supabase.table("users").insert({"name": name, "message": message}).execute()
        return "تمت الإضافة بنجاح!"
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
