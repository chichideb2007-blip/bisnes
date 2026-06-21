from flask import Flask
import os
from supabase import create_client, Client

app = Flask(__name__)

# إعداد الاتصال
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

@app.route('/')
def home():
    return "السيرفر يعمل!"

@app.route('/data')
def get_data():
    try:
        # هنا ضعي اسم الجدول الخاص بكِ مكان كلمة 'users'
        response = supabase.table("users").select("*").execute()
        return str(response.data)
    except Exception as e:
        return f"خطأ: {str(e)}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
