# هذا الجزء نزيدوه في main.py باش يقرأ المنتجات
@app.route('/products')
def get_products():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    comp_id = session['company_id']
    # جيب المنتجات الخاصة بهاد الشركة برك
    response = supabase.table("products").select("*").eq("company_id", comp_id).execute()
    return render_template('products.html', products=response.data)

@app.route('/add_product', methods=['POST'])
def add_product():
    if 'user' not in session: return "Unauthorized", 401
    
    comp_id = session['company_id']
    name = request.form.get('name')
    price = request.form.get('price')
    quantity = request.form.get('quantity')
    
    supabase.table("products").insert({
        "company_id": int(comp_id),
        "name": name,
        "price": float(price),
        "quantity": int(quantity)
    }).execute()
    
    return redirect(url_for('get_products'))
