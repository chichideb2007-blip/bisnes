import os
from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client

app = Flask(__name__)

# جلب الإعدادات من Render
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')

# التأكد من أن الإعدادات موجودة قبل إنشاء العميل
if url and key:
    supabase = create_client(url, key)
else:
    supabase = None

@app.route('/')
def home():
    return "الموقع يعمل بنجاح! - الصفحة الرئيسية"

@app.route('/orders')
def orders():
    if not supabase:
        return "خطأ في الاتصال بقاعدة البيانات"
    res = supabase.table("orders").select("*").execute()
    return str(res.data) # تجربة بسيطة للتأكد من جلب البيانات

if __name__ == '__main__':
    app.run()