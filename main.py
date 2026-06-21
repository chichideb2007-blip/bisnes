from flask import Flask, request, render_template
from supabase import create_client
import os

app = Flask(__name__)

# إعداد Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/users')
def get_users():
    response = supabase.table("users").select("*").execute()
    return render_template('users.html', users=response.data)

@app.route('/add')
def add_data():
    try:
        user_name = request.args.get('username', 'شيمو')
        supabase.table("users").insert({
            "username": user_name,
            "password": "123"
        }).execute()
        return "تمت الإضافة بنجاح!"
    except Exception as e:
        if "23505" in str(e):
            return "هذا المستخدم موجود بالفعل في قاعدة البيانات."
        return f"حدث خطأ: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)
