from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_secret_key' # استبدليها بمفتاح سري خاص بك

# إعدادات المتجر الافتراضية
settings = {
    'company_name': 'متجري الإلكتروني',
    'currency': 'DA', # قمت بتحديثها لتكون DA كما طلبتِ
    'telegram_token': '',
    'telegram_chat_id': '',
    'instagram_url': ''
}

# --- المسارات (Routes) ---

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', settings=settings)

@app.route('/settings', methods=['GET', 'POST'])
def settings_page():
    global settings
    if request.method == 'POST':
        settings['company_name'] = request.form.get('company_name')
        settings['currency'] = request.form.get('currency')
        settings['telegram_token'] = request.form.get('telegram_token')
        settings['telegram_chat_id'] = request.form.get('chat_id')
        settings['instagram_url'] = request.form.get('instagram_url')
        return redirect(url_for('settings_page'))
    return render_template('settings.html', settings=settings)

@app.route('/products', methods=['GET', 'POST'])
def products():
    # منطق إضافة منتج جديد (POST) أو عرض المنتجات (GET)
    if request.method == 'POST':
        # أضيفي هنا منطق حفظ المنتج في قاعدة البيانات
        return redirect(url_for('products'))
        
    products_list = [] # استبدليها بالبيانات الحقيقية من قاعدة البيانات
    return render_template('products.html', products=products_list, currency=settings['currency'], search=request.args.get('search'))

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    # منطق إضافة طلبية جديدة (POST) أو عرض الطلبات (GET)
    if request.method == 'POST':
        # أضيفي هنا منطق حفظ الطلبية في قاعدة البيانات
        return redirect(url_for('orders'))
        
    orders_list = [] # استبدليها بالبيانات الحقيقية من قاعدة البيانات
    return render_template('orders_dashboard.html', orders=orders_list, currency=settings['currency'])

@app.route('/stats')
def stats():
    # بيانات الإحصائيات
    daily = {"السبت": 100, "الأحد": 150, "الاثنين": 120}
    monthly = {"جانفي": 500, "فيفري": 700}
    yearly = {"2026": 5000}
    
    return render_template('stats.html', 
                           total_sales=1250, 
                           total_expenses=300, 
                           total_orders=15, 
                           currency=settings['currency'],
                           daily=daily, monthly=monthly, yearly=yearly)

# --- مسارات الحذف ---

@app.route('/delete_product/<int:id>', methods=['POST'])
def delete_product(id):
    # أضيفي هنا منطق حذف المنتج
    return redirect(url_for('products'))

@app.route('/delete_order/<int:id>', methods=['POST'])
def delete_order(id):
    # أضيفي هنا منطق حذف الطلبية
    return redirect(url_for('orders'))

# مسار إضافي لعرض تفاصيل الطلب (مطلوب في صفحة الطلبات)
@app.route('/view_order/<int:id>')
def view_order(id):
    return "تفاصيل الطلب رقم: " + str(id)

@app.route('/logout')
def logout():
    return "تم تسجيل الخروج"

if __name__ == '__main__':
    app.run(debug=True)
