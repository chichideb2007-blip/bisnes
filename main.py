from flask import Flask, request
import os
from supabase import create_client, Client

app = Flask(__name__)

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# صفحة لإضافة بيانات جديدة
@app.route('/add')
def add_data():
    name = request.args.get('name', 'شخص مجهول')
    message = request.args.get('message', 'مرحباً!')
    
    # إضافة البيانات للجدول (تأكدي أن اسم الجدول هو 'users')
    data = supabase.table("users").insert({"name": name, "message": message}).execute()
    return f"تمت إضافة: {name} - {message}"

# صفحة لعرض البيانات
@app.route('/data')
def get_data():
    response = supabase.table("users").select("*").execute()
    return str(response.data)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
