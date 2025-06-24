import datetime
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
        host TEXT, 
        reason TEXT,
        department TEXT,
        start_date TEXT,
        end_date TEXT

    )''')
    conn.commit()
    conn.close()

def update_schema():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE visitors ADD COLUMN quiz_passed INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.commit()
    conn.close()


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register')
def register():
    return render_template('form.html')

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    phone = request.form['phone']
    reason = request.form['reason']
    # Use the custom reason if 'Other' is selected
    if reason == 'Other':
        reason = request.form.get('other_reason', '').strip() or 'Other'
    host = request.form['host']
    department = request.form['department']
    start_date = request.form.get('start_date') or None
    end_date = request.form.get('end_date') or None

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
    INSERT INTO visitors 
    (name, phone, host, reason, department, start_date, end_date) 
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", (name, phone, host, reason, department, start_date, end_date))

    visitor_id = c.lastrowid
    conn.commit()
    conn.close()

    #  Save visitor_id to session
    session['visitor_id'] = visitor_id

    #  Redirect to profile page first
    return redirect(url_for('quiz', visitor_id=visitor_id))

@app.route('/admin')
def admin():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM visitors")
    visitors = c.fetchall()
    conn.close()
    return render_template('admin.html', data=visitors)


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
            return render_template('login.html', error="❌Invalid credentials...Try again")
        
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))   

@app.route('/quiz/<int:visitor_id>', methods=['GET', 'POST'])
def quiz(visitor_id):
    import os
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT department FROM visitors WHERE id = ?", (visitor_id,))
    row = c.fetchone()
    department = row[0] if row else None


    if not department:
        return "department not found for this visitor", 404

    department_path_map = {
        "Power Plant": "PPE/Power-Plant/",
        "Rolling Mill": "PPE/Rolling Mill/",
        "Steel Melting Shop": "PPE/Steel-Melting-Shop/",
    }

    instruction_map = {
        "Power Plant": [
            "Flame-retardant suits must be worn at all times.",
            "Use ear protection to prevent hearing damage.",
            "Gloves are required for handling any equipment.",
            "Safety boots must be worn to prevent injuries.",
            "Helmets are mandatory in all operational areas."
        ],
        "Rolling Mill": [
            "Wear cut-resistant gloves while working near rolling parts.",
            "Use safety goggles to prevent eye injuries.",
            "Reflective jackets must be worn for visibility.",
            "Safety boots are essential for foot protection.",
            "Helmets must be worn at all times on the floor."
        ],
        "Steel Melting Shop": [
            "Full body heat-resistant suits are mandatory.",
            "Face shields and high-temp gloves required.",
            "Helmet with face shield must be worn at all times.",
            "Avoid flammable materials near molten metal.",
            "Stay hydrated and avoid direct contact with hot surfaces.",
            "Report burns or injuries immediately to your supervisor."
        ],
        "Admin Office": [
            "Maintain decorum while on office premises.",
            "ID cards must be visibly worn.",
            "Visitors must stay in designated areas.",
            "Photography is strictly prohibited inside the office.",
            "Do not tamper with office equipment or files."
        ]
    }

    questions = [
        "Are you wearing the correct PPE?",
        "Do you understand emergency protocols?",
        "Will you report unsafe conditions?"
    ]

    image_dir = department_path_map.get(department)
    static_folder = os.path.join(app.root_path, "static")
    full_image_path = os.path.join(static_folder, image_dir) if image_dir else ""

    try:
        image_files = os.listdir(full_image_path)
    except FileNotFoundError:
        image_files = []

    ppe_images = [f"{image_dir}{img}" for img in image_files if img.lower().endswith(('.jpg', '.jpeg', '.png', '.avif'))]

    if request.method == "POST":
        answers = [request.form.get(f"q{i+1}") for i in range(len(questions))]
        if all(ans == "YES" for ans in answers):
            c.execute("UPDATE visitors SET quiz_passed = 1 WHERE id = ?", (visitor_id,))
            conn.commit()
            conn.close()
            return redirect(url_for("generate_qr", visitor_id=visitor_id))
        else:
            conn.close()
            return render_template("quiz_fail.html", area=department, visitor_id=visitor_id)

    conn.close()
    instructions = instruction_map.get(department, [])
    return render_template("quiz.html", visitor_id=visitor_id, area=department,
                           ppe_images=ppe_images, instructions=instructions, questions=questions)


    
@app.route('/qr/<int:visitor_id>')
def generate_qr(visitor_id):
    return redirect(url_for('visitor_profile', visitor_id=visitor_id))

@app.route('/profile/<int:visitor_id>')
def visitor_profile(visitor_id):
    if session.get('visitor_id') != visitor_id:
        return "❌ Access denied. You are not authorized to view this profile.", 403

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM visitors WHERE id = ?", (visitor_id,))
    visitor = c.fetchone()
    conn.close()
    if not visitor:
        return "<h3>Visitor not found.</h3>"

    return render_template('profile.html', visitor=visitor)



@app.route('/checkout/<int:visitor_id>')
def handle_checkout(visitor_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    checkout_time = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
    c.execute("UPDATE visitors SET status='Checked Out', checkout_time=? WHERE id=?", (checkout_time, visitor_id))
    conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/debug')
def debug():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM visitors")
    data = c.fetchall()
    conn.close()
    return {'data': data}

@app.route('/qr_image/<int:visitor_id>')
def qr_image(visitor_id):
    # QR should link to checkin route
    checkin_url = url_for('handle_checkin', visitor_id=visitor_id, _external=True)

    # Generate QR code with that URL
    img = qrcode.make(checkin_url)

    # Convert QR to byte stream for displaying
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)

    return send_file(buf, mimetype='image/png')

@app.route('/checkin/<int:visitor_id>')
def handle_checkin(visitor_id): 
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    from datetime import datetime
    now = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
    c.execute("UPDATE visitors SET checkin_time = ?, checkin_status = ? WHERE id = ?", 
              (now, 'Checked In', visitor_id))

    conn.commit()
    conn.close()

    return redirect(url_for('profile', visitor_id=visitor_id))

@app.template_filter('datetimeformat')
def datetimeformat(value):
    if not value:
        return ''
    try:
<<<<<<< HEAD
        # Try parsing as YYYY-MM-DD or YYYY-MM-DD HH:MM:SS
        if len(value) == 10:
            dt = datetime.strptime(value, '%Y-%m-%d')
        else:
            dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
=======
        
        if len(value) == 10:
            dt = datetime.strptime(value, '%d-%m-%Y')
        else:
            dt = datetime.strptime(value, '%d-%m-%Y %H:%M:%S')
>>>>>>> ea25a4e (changed database info)
        return dt.strftime('%d-%m-%Y')
    except Exception:
        return value

if __name__ == '__main__':
    init_db()
    update_schema()
    app.run(debug=True)
