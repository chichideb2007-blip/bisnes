from flask import Flask, render_template, request, redirect, session
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = "shimo-secure-2026"

# إعداد Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect('/login')
    user_id = session['user_id']
    
    # جلب إعدادات هذا العميل فقط
    settings = supabase.table('settings').select('*').eq('user_id', user_id).single().execute().data
    # جلب طلبيات هذا العميل فقط
    orders = supabase.table('orders').select('*').eq('user_id', user_id).execute().data
    
    return render_template('dashboard.html', settings=settings, orders=orders)

@app.route('/update-info', methods=['POST'])
def update_info():
    user_id = session.get('user_id')
    data = {
        "shop_name": request.form.get('shop_name'),
        "bot_token": request.form.get('bot_token'),
        "primary_color": request.form.get('primary_color')
    }
    supabase.table('settings').upsert({"user_id": user_id, **data}).execute()
    return redirect('/dashboard')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
