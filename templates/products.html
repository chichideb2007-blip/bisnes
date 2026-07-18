<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>إدارة المخزون</title>
    <!-- استدعاء مكتبة Supabase للتعامل مع الرفع في المتصفح -->
    <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; background-color: #f4f7f6; }
        .form-container { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; }
        input { width: 100%; padding: 10px; margin: 5px 0; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; }
        .btn-save { background-color: #28a745; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; width: 100%; }
        table { width: 100%; border-collapse: collapse; background: white; margin-top: 20px; }
        th, td { padding: 12px; border: 1px solid #ddd; text-align: center; }
        img { width: 50px; height: 50px; border-radius: 5px; object-fit: cover; }
        .btn-delete { background-color: red; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer; }
    </style>
</head>
<body>

    <h1>إدارة المخزون</h1>

    <div class="form-container">
        <h3>إضافة منتج جديد</h3>
        <form id="productForm" action="/products" method="POST">
            <input type="text" name="name" placeholder="اسم المنتج" required>
            <input type="number" name="quantity" placeholder="الكمية" required>
            <input type="number" step="0.01" name="price" placeholder="السعر" required>
            
            <!-- حقل مخفي لاستلام الرابط بعد الرفع -->
            <input type="hidden" name="product-images" id="image_url_input">
            
            <label style="display:block; margin-top:10px;">اختر صورة من المعرض:</label>
            <input type="file" id="fileInput" accept="image/*">
            
            <button type="submit" class="btn-save" id="submitBtn">حفظ المنتج</button>
        </form>
    </div>

    <table>
        <thead>
            <tr>
                <th>الصورة</th>
                <th>اسم المنتج</th>
                <th>الكمية</th>
                <th>السعر</th>
                <th>إجراءات</th>
            </tr>
        </thead>
        <tbody>
            {% for p in products %}
            <tr>
                <td>
                    {% if p['product-images'] %}
                        <img src="{{ p['product-images'] }}" alt="صورة">
                    {% else %}
                        <span>لا توجد</span>
                    {% endif %}
                </td>
                <td>{{ p.name }}</td>
                <td>{{ p.quantity }}</td>
                <td>{{ p.price }} دج</td>
                <td>
                    <form action="/delete_product/{{ p.id }}" method="POST">
                        <button type="submit" class="btn-delete">حذف</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <script>
        // --- إعداد Supabase ---
        // استبدلي الروابط بالقيم الحقيقية من مشروعك في Supabase (Settings > API)
        const supabase = supabase.createClient('YOUR_SUPABASE_URL', 'YOUR_SUPABASE_ANON_KEY');

        document.getElementById('productForm').onsubmit = async (e) => {
            const fileInput = document.getElementById('fileInput');
            
            if (fileInput.files.length > 0) {
                e.preventDefault(); // إيقاف الإرسال حتى نرفع الصورة أولاً
                const btn = document.getElementById('submitBtn');
                btn.innerText = "جاري الرفع...";
                btn.disabled = true;

                const file = fileInput.files[0];
                const fileName = Date.now() + '_' + file.name;

                // 1. رفع الصورة إلى الـ Bucket المسمى product-images
                const { data, error } = await supabase.storage
                    .from('product-images')
                    .upload(fileName, file);

                if (error) { 
                    alert('خطأ في رفع الصورة: ' + error.message); 
                    btn.innerText = "حفظ المنتج";
                    btn.disabled = false;
                    return; 
                }

                // 2. الحصول على الرابط العام للصورة المرفوعة
                const { data: publicURL } = supabase.storage
                    .from('product-images')
                    .getPublicUrl(fileName);

                // 3. وضع الرابط في الحقل المخفي وإرسال الفورم للسيرفر
                document.getElementById('image_url_input').value = publicURL.publicUrl;
                document.getElementById('productForm').submit();
            }
        };
    </script>
</body>
</html>
