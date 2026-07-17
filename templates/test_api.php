<?php
// 1. ضعي الـ Access Token الطويل هنا
$accessToken = '1833157664659159|dikLlwRsvK8Xn4ZfGoCNhJBfZCk';

// 2. الرابط الخاص بالـ API لجلب بيانات الحساب
$url = "https://graph.facebook.com/v20.0/me?fields=id,name&access_token=" . $accessToken;

// 3. إرسال الطلب باستخدام cURL
$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);
curl_close($ch);

// 4. عرض النتيجة
$data = json_decode($response, true);
print_r($data);
?>
