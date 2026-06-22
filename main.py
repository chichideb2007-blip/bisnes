from datetime import datetime

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # جلب طلبات اليوم فقط
    today = datetime.now().strftime('%Y-%m-%d')
    orders = supabase.table("orders").select("*").ilike("created_at", f"{today}%").execute()
    
    # حساب المجموع
    total_today = sum(item['price'] for item in orders.data)
    
    return render_template('users.html', orders=orders.data, total=total_today)
