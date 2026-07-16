from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
from collections import defaultdict
from datetime import datetime
import os
import time

app = Flask(__name__)
app.secret_key = 'secret_key_123'

# إعداد Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

def get_cid():
    return session.get('company_id')

# --- الإحصائيات مع المنحنيات (النسخة الكاملة) ---
@app.route('/stats')
def stats():
    cid = get_cid()
    if not cid: return redirect(url_for('login'))
    
    try:
        # 1. جلب الطلبات الخاصة بالشركة فقط
        res_orders = supabase.table("orders").select("total_price, created_at").eq("company_id_text", cid).execute()
        orders = res_orders.data or []
        
        # 2. جلب المصاريف (إذا وجد جدول المصاريف)
        try:
            res_expenses = supabase.table("expenses").select("amount, created_at").eq("company_id", cid).execute()
            expenses = res_expenses.data or []
        except:
            expenses = []
        
        # 3. تجهيز البيانات للمنحنيات (هذا الجزء هو ما يغذي ملف stats.html)
        daily_data = defaultdict(float)
        monthly_data = defaultdict(float)
        yearly_data = defaultdict(float)
        
        days_order = ["السبت", "الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
        months_order = ["جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان", "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]

        for o in orders:
            if o.get('created_at'):
                try:
                    dt = datetime.fromisoformat(o['created_at'].replace('Z', '+00:00'))
                    price = float(o.get('total_price', 0) or 0)
                    
                    # ملء البيانات حسب اليوم والشهر والسنة
                    day_name = days_order[dt.weekday() if dt.weekday() != 6 else 0]
                    month_name = months_order[dt.month - 1]
                    
                    daily_data[day_name] += price
                    monthly_data[month_name] += price
                    yearly_data[str(dt.year)] += price
                except:
                    continue

        return render_template('stats.html', 
                               total_sales=sum(float(o.get('total_price', 0) or 0) for o in orders),
                               total_expenses=sum(float(e.get('amount', 0) or 0) for e in expenses),
                               total_orders=len(orders),
                               daily=dict(daily_data),
                               monthly=dict(monthly_data),
                               yearly=dict(yearly_data))
    except Exception as e:
        return f"حدث خطأ في جلب بيانات الإحصائيات: {str(e)}"

# --- باقي المسارات (Products, Orders, Login) كما في الكود السابق ---
# (تأكدي من استخدام cid في كل استعلام .eq("company_id_text", cid))

@app.route('/login', methods=['POST'])
def login():
    # هنا يجب أن تضعي المنطق الصحيح لتسجيل الدخول
    session['company_id'] = "1" 
    return redirect(url_for('stats'))

if __name__ == '__main__':
    app.run(debug=True)
