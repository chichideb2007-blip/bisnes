from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your-super-secure-random-key")

# إعداد Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    # التحقق من أن الشركة مسجلة
    company_id = session.get('user_id')
    if not company_id:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        data = {
            "customer_name": request.form.get('customer_name'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('total_price', 0)),
            "customer_phone": request.form.get('customer_phone'),
            "company_id": company_id  # هذا الـ ID هو الذي سيطابق auth.uid() في قاعدة البيانات
        }
        supabase.table('orders').insert(data).execute()
        return redirect(url_for('orders'))
    
    # جلب الطلبيات الخاصة بهذه الشركة فقط
    response = supabase.table('orders').select('*').eq('company_id', company_id).execute()
    return render_template('users.html', orders=response.data)

@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    company_id = session.get('user_id')
    if not company_id:
        return redirect(url_for('login'))
    
    # الحذف الآن محمي بسياسة RLS ولن ينجح إلا إذا طابق company_id
    supabase.table('orders').delete().eq('id', order_id).eq('company_id', company_id).execute()
    return redirect(url_for('orders'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
