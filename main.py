from flask import Flask, render_template

app = Flask(__name__, template_folder='templates')

@app.route('/')
def home():
    return "الموقع يعمل بنجاح! - <a href='/login'>اذهب لصفحة الدخول</a>"

@app.route('/login')
def login():
    return render_template('login.html')

if __name__ == '__main__':
    app.run()
