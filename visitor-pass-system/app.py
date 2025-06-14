from flask import Flask, render_template, request, redirect, url_for, send_file, session
from datetime import datetime
import sqlite3
import qrcode
import io

app = Flask(__name__)
app.secret_key = 'my_secret_visitor_pass_2025'
DB_NAME = 'database.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS visitors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    phone TEXT,
                    reason TEXT,
                    host TEXT,
                    quiz_passed INTEGER,
                    checkin_status TEXT,
                    checkin_time TEXT,
                    checkout_time TEXT
                )''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('form.html')

@app.route('/about')
def about():
    return "<h2>About Us</h2><p>This is a smart visitor system for safety and tracking.</p>"

@app.route('/profile')
def profile():
    return "<h2>Admin Profile</h2><p>Welcome, Admin!</p>"

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    phone = request.form['phone']
    reason = request.form['reason']
    host = request.form['host']
    area = request.form['area']

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO visitors (name, phone, reason, host, area, quiz_passed, checkin_status, checkin_time, checkout_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (name, phone, reason, host, area, 0, 'Not Checked In', ", "))
    visitor_id = c.lastrowid
    conn.commit()
    conn.close()

    return redirect(url_for('quiz', visitor_id=visitor_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Simple static check (replace with DB check later)
        if username == 'admin' and password == 'admin123':
            session['user'] = username
            return redirect(url_for('admin'))
        else:
            return "❌ Invalid credentials. <a href='/login'>Try again</a>"

    return '''
        <h2>Login</h2>
        <form method="post">
            Username: <input type="text" name="username" required><br>
            Password: <input type="password" name="password" required><br>
            <button type="submit">Login</button>
        </form>
    '''

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))   

@app.route('/quiz/<int:visitor_id>', methods=['GET', 'POST'])
def quiz(visitor_id):
    if request.method == 'POST':
        q1 = request.form.get('q1')
        q2 = request.form.get('q2')
        q3 = request.form.get('q3')

        # Check if all answers are correct
        if q1 == 'yes' and q2 == 'yes' and q3 == 'yes':
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE visitors SET quiz_passed = 1 WHERE id = ?", (visitor_id,))
            conn.commit()
            conn.close()
            return redirect(url_for('generate_qr', visitor_id=visitor_id))
        else:
            return """
                <h2>❌ Quiz Failed</h2>
                <p>Please follow all safety protocols to continue.</p>
                <a href='/'>Back to Home</a>
            """
    return render_template('quiz.html')

@app.route('/qr/<int:visitor_id>')
def generate_qr(visitor_id):
    img = qrcode.make(f"VisitorID:{visitor_id}")
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/admin')
def admin():
    if session.get('user') != 'admin':
        return "<h3>❌ Unauthorized Access</h3><p>You must be logged in as admin to view this page.</p><a href='/login'>Login as Admin</a>"
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM visitors")
    data = c.fetchall()
    conn.close()
    return render_template('admin.html', data=data)

@app.route('/checkin/<int:visitor_id>')
def checkin(visitor_id):
    if session.get('user') != 'admin':
        return "❌ Unauthorized", 403
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE visitors SET checkin_status = 'Checked In', checkin_time = ? WHERE id = ?", (now, visitor_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/checkout/<int:visitor_id>')
def checkout(visitor_id):
    if session.get('user') != 'admin':
        return "❌ Unauthorized", 403
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE visitors SET checkin_status = 'Checked Out', checkout_time = ? WHERE id = ?", (now, visitor_id))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/debug')
def debug():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM visitors")
    data = c.fetchall()
    conn.close()
    return {'data': data}

if __name__ == '__main__':
    app.run(debug=True)