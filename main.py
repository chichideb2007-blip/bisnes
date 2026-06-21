from flask import Flask, request
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

@app.route('/add')
def add_data():
    name = request.args.get('name', 'شيماء')
    message = request.args.get('message', 'مرحباً')
    # تأكدي أن اسم الجدول هو 'users'
    data = supabase.table("users").insert({"name": name, "message": message}).execute()
    return f"تمت إضافة: {name} - {message}"

@app.route('/data')
def get_data():
    response = supabase.table("users").select("*").execute()
    return str(response.data)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
