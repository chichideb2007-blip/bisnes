from flask import request

# دالة إضافة طلب جديد
@app.route('/add', methods=['POST'])
def add_order():
    name = request.form.get('product_name')
    price = request.form.get('price')
    supabase.table("orders").insert({"product_name": name, "price": price}).execute()
    return redirect(url_for('dashboard'))

# دالة حذف طلب
@app.route('/delete/<int:order_id>')
def delete_order(order_id):
    supabase.table("orders").delete().eq("id", order_id).execute()
    return redirect(url_for('dashboard'))
