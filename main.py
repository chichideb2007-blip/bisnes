import os
from flask import Flask, render_template, request, session, redirect
from supabase import create_client

app = Flask(__name__)
app.secret_key = 'shimo_final_pro_2026'

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key) if url and key else None

@app.route('/')
def index(): return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user'] = request.form.get('username')
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/dashboard', methods=['GET'])
def dashboard():
    if 'user' not in session: return redirect('/login')
    orders = []
    if supabase:
        try:
            # جلب الطلبات مرتبة حسب الأحدث
            response = supabase.table("orders").select("*").order("created_at", descending=True).execute()
            orders = response.data if response.data else []
        except Exception as e: print(f"Error: {e}")
    return render_template('dashboard.html', user=session['user'], orders=orders)

@app.route('/add-order', methods=['POST'])
def add_order():
    if 'user' not in session: return redirect('/login')
    if supabase:
        try:
            supabase.table("orders").insert({
                "customer_name": request.form.get('name'),
                "product_name": request.form.get('product'),
                "total_price": float(request.form.get('price', 0)),
                "customer_phone": request.form.get('phone')
            }).execute()
        except Exception as e: print(f"Error adding: {e}")
    return redirect('/dashboard')

@app.route('/delete-order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    if 'user' not in session: return redirect('/login')
    if supabase:
        try:
            # حذف الطلب باستخدام الـ id الخاص به
            supabase.table("orders").delete().eq("id", order_id).execute()
        except Exception as e: print(f"Error deleting: {e}")
    return redirect('/dashboard')

@app.route('/edit-order/<int:order_id>', methods=['POST'])
def edit_order(order_id):
    if 'user' not in session: return redirect('/login')
    if supabase:
        try:
            # تحديث بيانات الطلب بناءً على الـ id
            supabase.table("orders").update({
                "customer_name": request.form.get('name'),
                "product_name": request.form.get('product'),
                "total_price": float(request.form.get('price', 0)),
                "customer_phone": request.form.get('phone')
            }).eq("id", order_id).execute()
        except Exception as e: print(f"Error editing: {e}")
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
