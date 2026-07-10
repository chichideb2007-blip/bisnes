# --- المسارات ---

# (المسارات السابقة موجودة هنا كما هي)

# --- إدارة المنتجات (المخزن) والبحث ---

@app.route('/products', methods=['GET', 'POST'])
def products():
    if 'company_id' not in session: return redirect(url_for('login'))
    comp_id = session['company_id']
    
    if request.method == 'POST':
        # استقبال ملف الصورة
        image_file = request.files.get('product_image')
        image_url = ""
        
        if image_file and image_file.filename != '':
            try:
                unique_filename = f"{uuid.uuid4()}_{image_file.filename}"
                supabase.storage.from_("product-images").upload(unique_filename, image_file.read())
                image_url = supabase.storage.from_("product-images").get_public_url(unique_filename)
            except Exception as e:
                return f"خطأ في رفع الصورة: {e}"
        
        new_prod = {
            "name": request.form.get("name"),
            "quantity": int(request.form.get("quantity", 0)),
            "price": float(request.form.get("price", 0)),
            "image_url": image_url,
            "company_id_text": comp_id
        }
        supabase.table("inventory").insert(new_prod).execute()
        return redirect(url_for('products'))
    
    response = supabase.table("inventory").select("*").eq("company_id_text", comp_id).execute()
    return render_template('products.html', products=response.data or [])

# --- مسار البحث الجديد ---
@app.route('/search_products')
def search_products():
    if 'company_id' not in session: return redirect(url_for('login'))
    
    query = request.args.get('q', '')
    comp_id = session['company_id']
    
    # البحث في جدول inventory بناءً على اسم المنتج
    # ilike تعني بحث غير حساس لحالة الأحرف
    response = supabase.table("inventory").select("*") \
        .eq("company_id_text", comp_id) \
        .ilike("name", f"%{query}%").execute()
        
    return render_template('products.html', products=response.data or [])

@app.route('/delete_product/<int:prod_id>')
def delete_product(prod_id):
    if 'company_id' not in session: return redirect(url_for('login'))
    supabase.table("inventory").delete().eq("id", prod_id).eq("company_id_text", session['company_id']).execute()
    return redirect(url_for('products'))

# (باقي المسارات الخاصة بالطلبيات والإحصائيات تبقى كما هي في ملفك)
