from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3
import qrcode
import io

app = Flask(__name__)
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
                    checkin_status TEXT
                )''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('form.html')

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    phone = request.form['phone']
    reason = request.form['reason']
    host = request.form['host']

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO visitors (name, phone, reason, host, quiz_passed, checkin_status) VALUES (?, ?, ?, ?, ?, ?)",
              (name, phone, reason, host, 0, 'Not Checked In'))
    visitor_id = c.lastrowid
    conn.commit()
    conn.close()

    return redirect(url_for('quiz', visitor_id=visitor_id))

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
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM visitors")
    data = c.fetchall()
    conn.close()
    return render_template('admin.html', data=data)

@app.route('/checkin/<int:visitor_id>')
def checkin(visitor_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE visitors SET checkin_status = 'Checked In' WHERE id = ?", (visitor_id,))
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
