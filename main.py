from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client
import os
from datetime import datetime

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'your_secret_key'

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# --- المسارات ---

@app.route('/stats')
def stats():
    response = supabase.table("orders").select("*").execute()
    orders = response.data
    
    # 1. إنشاء قوالب ثابتة بالترتيب (لضمان ظهورها كاملة)
    daily = {day: 0 for day in ['السبت', 'الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة']}
    monthly = {month: 0 for month in ['جانفي', 'فيفري', 'مارس', 'أفريل', 'ماي', 'جوان', 'جويلية', 'أوت', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']}
    yearly = {str(year): 0 for year in range(2026, 2030)} # من 2026 إلى 2029
    
    # قواميس للترجمة
    days_map = {'Monday': 'الاثنين', 'Tuesday': 'الثلاثاء', 'Wednesday': 'الأربعاء', 'Thursday': 'الخميس', 'Friday': 'الجمعة', 'Saturday': 'السبت', 'Sunday': 'الأحد'}
    months_map = {'January': 'جانفي', 'February': 'فيفري', 'March': 'مارس', 'April': 'أفريل', 'May': 'ماي', 'June': 'جوان', 'July': 'جويلية', 'August': 'أوت', 'September': 'سبتمبر', 'October': 'أكتوبر', 'November': 'نوفمبر', 'December': 'ديسمبر'}

    # 2. تعبئة القوالب بالبيانات الحقيقية
    for order in orders:
        created_at = order.get('created_at', datetime.now().isoformat())
        dt = datetime.strptime(created_at[:10], '%Y-%m-%d')
        
        # استخراج الأسماء العربية
        day_name = days_map.get(dt.strftime('%A'))
        month_name = months_map.get(dt.strftime('%B'))
        year_name = str(dt.year)
        
        # إضافة السعر للقالب
        if day_name in daily: daily[day_name] += float(order.get('total_price', 0))
        if month_name in monthly: monthly[month_name] += float(order.get('total_price', 0))
        if year_name in yearly: yearly[year_name] += float(order.get('total_price', 0))
        
    return render_template('stats.html', daily=daily, monthly=monthly, yearly=yearly)

# باقي المسارات (dashboard, orders, delete_order...) تبقى كما هي
@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        data = {
            "customer_name": request.form.get("customer_name"),
            "customer_phone": request.form.get("customer_phone"),
            "product_name": request.form.get("product_name"),
            "total_price": float(request.form.get("total_price", 0)),
            "created_at": datetime.now().isoformat() # مهم جداً لتسجيل التاريخ
        }
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    response = supabase.table("orders").select("*").execute()
    return render_template('orders_dashboard.html', orders=response.data)

if __name__ == '__main__':
    app.run(debug=True)
