import os
from flask import Flask, render_template, request, redirect, session
from supabase import create_client

# 1. أول شيء: تعريف التطبيق (يجب أن يكون هنا في الأعلى)
app = Flask(__name__)
app.secret_key = 'chaima_pro_2026'

# 2. ثاني شيء: الاتصال بقاعدة البيانات
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# 3. ثالث شيء: المسارات (Routes)
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # تحقق من المستخدم في قاعدة البيانات
        response = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
        if response.data:
            session['user'] = username
            return redirect('/dashboard')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    # جلب البيانات الخاصة بالمدير الحالي فقط
    response = supabase.table("orders").select("*").eq("manager_id", session['user']).execute()
    orders = response.data
    total = sum(float(item.get('total_price', 0)) for item in orders)
    return render_template('users.html', orders=orders, total=total)

@app.route('/add', methods=['POST'])
def add():
    if 'user' not in session: return redirect('/')
    data = {
        "product_name": request.form.get('product_name'),
        "total_price": request.form.get('total_price'),
        "manager_id": session['user']
    }
    supabase.table("orders").insert(data).execute()
    return redirect('/dashboard')

@app.route('/delete/<int:id>')
def delete(id):
    if 'user' not in session: return redirect('/')
    supabase.table("orders").delete().eq("id", id).execute()
    return redirect('/dashboard')

# 4. رابع شيء: تشغيل التطبيق (يجب أن يكون في النهاية)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
