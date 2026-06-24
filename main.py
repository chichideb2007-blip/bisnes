from datetime import datetime

@app.route('/')
def dashboard():
    # جلب الطلبات من Supabase
    orders = supabase.table("orders").select("*").execute().data
    
    # حساب المجاميع
    now = datetime.now()
    daily_total = sum(o['total_price'] for o in orders if datetime.fromisoformat(o['created_at'][:10]) == now.date())
    monthly_total = sum(o['total_price'] for o in orders if datetime.fromisoformat(o['created_at'][:7]) == now.strftime("%Y-%m"))
    yearly_total = sum(o['total_price'] for o in orders if datetime.fromisoformat(o['created_at'][:4]) == now.strftime("%Y"))
    
    return render_template('dashboard.html', 
                           orders=orders, 
                           settings=get_settings(),
                           daily_total=daily_total,
                           monthly_total=monthly_total,
                           yearly_total=yearly_total)
