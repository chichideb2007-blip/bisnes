import os
from flask import Flask, render_template, request, redirect, session
from flask_mail import Mail, Message
from supabase import create_client

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')

# الاتصال بـ Supabase باستخدام المتغيرات الموجودة في Render
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

mail = Mail(app)

# دالة إرسال الإيميل (تأخذ الإعدادات من جدول manager_settings)
def send_dynamic_email(manager_id, subject, body):
    response = supabase.table("manager_settings").select("*").eq("manager_id", manager_id).execute()
    if not response.data: return
    
    cfg = response.data[0]
    
    app.config.update(
        MAIL_SERVER=cfg['smtp_server'],
        MAIL_PORT=int(cfg['smtp_port']),
        MAIL_USERNAME=cfg['email_address'],
        MAIL_PASSWORD=cfg['email_password'],
        MAIL_USE_TLS=True
    )
    
    mail_sender = Mail(app)
    msg = Message(subject, sender=cfg['email_address'], recipients=[cfg['email_address']])
    msg.body = body
    mail_sender.send(msg)

@app.route('/save-settings', methods=['POST'])
def save_settings():
    if 'user' not in session: return redirect('/login')
    
    data = {
        "manager_id": session['user'],
        "smtp_server": request.form.get('smtp_server'),
        "smtp_port": int(request.form.get('smtp_port')),
        "email_address": request.form.get('email_address'),
        "email_password": request.form.get('email_password')
    }
    # بما أن الجدول موجود، نستخدم upsert لتحديث البيانات
    supabase.table("manager_settings").upsert(data, on_conflict="manager_id").execute()
    return redirect('/dashboard')

if __name__ == '__main__':
    app.run(debug=True)
