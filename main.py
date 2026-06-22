import os
from flask import Flask, render_template, request, redirect, session
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'chaima_pro_2026'

# إعداد الاتصال
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    try:
        # جلب البيانات وترتيبها من الأحدث للأقدم
        response = supabase.table("orders").select("*").order("id", desc=True).execute()
        orders = response.data
        # حساب إجمالي المبيعات بدقة
        total = sum(float(item.get('total_price', 0)) for item in orders)
        return render_template('users.html', orders=orders, total=total)
    except Exception as e:
        return f"حدث خطأ في جلب البيانات: {e}"

@app.route('/add', methods=['POST'])
def add():
    try:
        data = {
            "product_name": request.form.get('product_name'),
            "total_price": request.form.get('total_price'),
            "customer_name": request.form.get('customer_name')
        }
        supabase.table("orders").insert(data).execute()
    except Exception as e:
        print(f"خطأ في الإضافة: {e}")
    return redirect('/dashboard')

@app.route('/delete/<int:order_id>')
def delete(order_id):
    supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect('/dashboard')
