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
        area TEXT,
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
    area = request.form['area']
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute("INSERT INTO visitors (name, phone, reason, host, area, quiz_passed, checkin_status) VALUES (?, ?, ?, ?, ?, ?, ?)",
          (name, phone, reason, host, area, 0, 'Not Checked In'))

    visitor_id = c.lastrowid
    conn.commit()
    conn.close()

    return redirect(url_for('quiz', visitor_id=visitor_id))

@app.route("/quiz/<int:visitor_id>", methods=["GET", "POST"])
def quiz(visitor_id):
    import os
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Get area from database
    c.execute("SELECT area FROM visitors WHERE id = ?", (visitor_id,))
    row = c.fetchone()
    area = row[0] if row else None

    if not area:
        return "Area not found for this visitor", 404

    # POST: If form submitted
    if request.method == "POST":
        # You could validate answers here if needed
        c.execute("UPDATE visitors SET quiz_passed = 1 WHERE id = ?", (visitor_id,))
        conn.commit()
        conn.close()
        return redirect(url_for("generate_qr", visitor_id=visitor_id))

    # GET: Show quiz form
    area_path_map = {
        "Power Plant": "PPE/Power-Plant/",
        "Rolling Mill": "PPE/Rolling Mill/",
        "Steel Melting Shop": "PPE/Steel-Melting-Shop/"
    }

    image_dir = area_path_map.get(area)
    if not image_dir:
        return f"No PPE folder found for area: {area}", 404

    static_folder = os.path.join(app.root_path, "static")
    full_image_path = os.path.join(static_folder, image_dir)

    try:
        image_files = os.listdir(full_image_path)
    except FileNotFoundError:
        image_files = []

    ppe_images = [f"{image_dir}{img}" for img in image_files if img.lower().endswith(('.jpg', '.jpeg', '.png', '.avif'))]

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
        ]
    }

    instructions = instruction_map.get(area, [])
    questions = [
        "Are you wearing the correct PPE?",
        "Do you understand emergency protocols?",
        "Will you report unsafe conditions?"
    ]

    return render_template("quiz.html", visitor_id=visitor_id, area=area,
                           ppe_images=ppe_images, instructions=instructions, questions=questions)


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
