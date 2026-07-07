import os
from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client

app = Flask(__name__)

# جلب المتغيرات
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

# محاولة اتصال بسيطة جداً
supabase = None
if url and key:
    supabase = create_client(url, key)

@app.route('/')
def home():
    return "السيرفر يعمل بنجاح!"

@app.route('/login')
def login():
    return render_template('login.html')

# تجربة مسار الطلبيات بدون تعقيد
@app.route('/orders')
def orders():
    return "صفحة الطلبيات"

if __name__ == '__main__':
    app.run()
