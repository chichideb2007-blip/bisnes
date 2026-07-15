from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key")

# إعداد Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if 'company_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # هذه البيانات تطابق الأعمدة التي رأيتها في الفيديو
        data = {
            "company_id": str(session['company_id']),
            "customer_name": request.form.get('customer_name'),
            "customer_phone": request.form.get('phone'),
            "product_name": request.form.get('product_name'),
            "total_price": float(request.form.get('price') or 0.0),
            "status": "new"  # إضافة قيمة افتراضية للعمود status
        }
        
        try:
            # الحفظ في جدول orders
            supabase.table("orders").insert(data).execute()
        except Exception as e:
            print(f"خطأ في الحفظ: {e}")
            
        return redirect(url_for('orders'))
    
    # جلب البيانات لعرضها في الجدول
    res = supabase.table("orders").select("*").eq("company_id", str(session['company_id'])).execute()
    return render_template('orders_dashboard.html', orders=res.data or [])

# ... باقي المسارات (login, dashboard, products) كما هي
