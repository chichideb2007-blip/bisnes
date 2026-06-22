import os
from flask import Flask, render_template, request, redirect, session
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'chaima_pro_2026'

supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

@app.route('/dashboard')
def dashboard():
    # التحقق من أن المستخدم مسجل دخول (نفترض أننا نخزن الـ username في session)
    if 'user' not in session: return redirect('/')
    
    # جلب الطلبات الخاصة بهذا المدير فقط باستخدام manager_id
    current_user = session['user']
    response = supabase.table("orders").select("*").eq("manager_id", current_user).order("id", desc=True).execute()
    
    orders = response.data
    # حساب الإجمالي للمدير الحالي فقط
    total = sum(float(item.get('total_price') or 0) for item in orders)
    
    return render_template('users.html', orders=orders, total=total)

@app.route('/add', methods=['POST'])
def add():
    if 'user' not in session: return redirect('/')
    
    # إضافة الطلب مع تسجيل الـ manager_id
    data = {
        "product_name": request.form.get('product_name'),
        "total_price": request.form.get('total_price'),
        "manager_name": request.form.get('manager_name'), # إذا كان مطلوباً
        "manager_id": session['user'] 
    }
    supabase.table("orders").insert(data).execute()
    return redirect('/dashboard')

# ... (باقي الدوال مثل الحذف)
