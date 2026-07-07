from flask import Flask, render_template, request, redirect, url_for
# ... (بقية الـ imports الموجودة عندك)

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if request.method == 'POST':
        # الحصول على البيانات من الفورم
        data = {
            "customer_name": request.form.get("customer_name"),
            "phone": request.form.get("phone"),
            "product": request.form.get("product"),
            "price": request.form.get("price")
        }
        # حفظ في Supabase
        supabase.table("orders").insert(data).execute()
        return redirect(url_for('orders'))
    
    # جلب الطلبيات لعرضها
    response = supabase.table("orders").select("*").execute()
    return render_template('orders_dashboard.html', orders=response.data)
