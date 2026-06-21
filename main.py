from flask import Flask
import os
from supabase import create_client, Client

app = Flask(__name__)

# إعداد الاتصال بـ Supabase
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

@app.route('/')
def home():
    try:
        # تجربة بسيطة للاتصال بقاعدة البيانات
        return "تم الاتصال بنجاح بـ Supabase!"
    except Exception as e:
        return f"حدث خطأ في الاتصال: {str(e)}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
