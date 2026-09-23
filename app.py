import json
import os
import sqlite3
from functools import wraps
from pathlib import Path
from datetime import datetime

from flask import Flask, jsonify, request, session, render_template, send_from_directory, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ============================================================
# RCS ROBOTICS CLUB - SINGLE FLASK BACKEND
# ============================================================

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
DB = DATA_DIR / "rcs.db"
UPLOADS = BASE / "static" / "uploads"
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "rcs-dev-secret-change-me")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


def now():
    return datetime.now().isoformat(timespec="seconds")


def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def rows(table):
    con = db()
    try:
        return [dict(row) for row in con.execute(f"SELECT * FROM {table}").fetchall()]
    finally:
        con.close()


def json_body():
    return request.get_json(silent=True) or {}


def text_value(data, key, default=""):
    value = data.get(key, default)
    return default if value is None else str(value).strip()


def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"success": False, "error": "Authentication required."}), 401
        return fn(*args, **kwargs)
    return wrapper


def allowed_image(filename):
    return bool(filename) and "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def save_upload(file):
    if not file or not file.filename:
        raise ValueError("No file selected.")
    if not allowed_image(file.filename):
        raise ValueError("Allowed image types: PNG, JPG, JPEG, WEBP, GIF.")

    filename = secure_filename(file.filename)
    stem, suffix = os.path.splitext(filename)
    path = UPLOADS / filename
    counter = 1
    while path.exists():
        path = UPLOADS / f"{stem}-{counter}{suffix}"
        counter += 1
    file.save(path)
    return f"/static/uploads/{path.name}"


def init_db():
    con = db()
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('faculty', 'member')),
            active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT,
            department TEXT,
            year TEXT,
            bio TEXT,
            image_url TEXT,
            skills TEXT,
            featured INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT,
            description TEXT,
            tech TEXT,
            status TEXT,
            image_url TEXT,
            demo_url TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date TEXT,
            time TEXT,
            venue TEXT,
            description TEXT,
            image_url TEXT,
            registration_url TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            topic TEXT,
            difficulty TEXT,
            description TEXT,
            questions_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            topic TEXT,
            description TEXT,
            game_type TEXT,
            difficulty TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS learning (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            level TEXT,
            category TEXT,
            description TEXT,
            content TEXT,
            order_no INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            type TEXT DEFAULT 'idea',
            title TEXT,
            message TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'new'
        );
        """)

    # Repair columns for older databases.
    for table in ("members", "projects", "events", "quizzes", "games", "learning"):
        existing = {r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()}
        if "created_at" not in existing:
            con.execute(f"ALTER TABLE {table} ADD COLUMN created_at TEXT")

    demo_users = [
        ("RCS Faculty", "faculty@rcs-sastra.org", "RCS@2026", "faculty"),
        ("RCS Member", "member@rcs-sastra.org", "RCS@2026", "member"),
    ]
    for name, email, password, role in demo_users:
        user = con.execute("SELECT id FROM users WHERE lower(email)=lower(?)", (email,)).fetchone()
        if user:
            con.execute("UPDATE users SET name=?, role=?, active=1 WHERE id=?", (name, role, user["id"]))
        else:
            con.execute(
                "INSERT INTO users(name,email,password,role,active) VALUES(?,?,?,?,1)",
                (name, email, generate_password_hash(password), role),
            )

    if con.execute("SELECT COUNT(*) FROM members").fetchone()[0] == 0:
        con.executemany(
            "INSERT INTO members(name,role,department,year,bio,image_url,skills,featured,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
            [
                ("RCS Core Team", "Club Lead", "Electronics & Communication Engineering", "3rd Year", "Leads builds, workshops and competitions.", "", "Embedded Systems, Robotics, ROS", 1, now()),
                ("RCS Core Team", "Technical Lead", "Electrical & Electronics Engineering", "3rd Year", "Owns robot architecture, electronics and integration.", "", "Arduino, ESP32, PCB, Control", 1, now()),
            ],
        )

    if con.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 0:
        con.executemany(
            "INSERT INTO projects(title,category,description,tech,status,image_url,demo_url,created_at) VALUES(?,?,?,?,?,?,?,?)",
            [
                ("Autonomous Line Follower", "Autonomy", "Fast, robust line-following robot with PID control and sensor fusion.", "ESP32, IR array, PID", "Prototype", "", "", now()),
                ("Predictive Conveyor Intelligence", "Industrial Robotics", "Sensor + vision pipeline for detecting belt-joint wear and abnormal motion.", "ESP32, Python, OpenCV, ML", "In Progress", "", "", now()),
            ],
        )

    if con.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0:
        con.executemany(
            "INSERT INTO events(title,date,time,venue,description,image_url,registration_url,created_at) VALUES(?,?,?,?,?,?,?,?)",
            [
                ("RCS Robotics Induction", "2026-09-15", "17:00", "SASTRA Campus", "Meet the team, see our robots and choose a technical track.", "", "", now()),
                ("Arduino + Sensors Bootcamp", "2026-09-22", "16:30", "Innovation Lab", "Hands-on workshop covering GPIO, PWM, sensors and motor control.", "", "", now()),
            ],
        )

    if con.execute("SELECT COUNT(*) FROM learning").fetchone()[0] == 0:
        lessons = [
            ("01 • Robotics Foundations", "Beginner", "Foundations", "Understand sensors, actuators, controllers, feedback and the basic robot loop.", "A robot senses the world, decides what to do, and acts.", 1),
            ("02 • Electronics & Embedded", "Beginner", "Electronics", "Learn digital/analog I/O, PWM, ADC, interrupts and serial protocols.", "Start with GPIO, pull-ups, ADC, PWM, UART, I2C and SPI.", 2),
            ("03 • Motors & Motion", "Beginner", "Actuation", "DC motors, servos, steppers, encoders and H-bridges.", "Understand torque, speed, gearing and bidirectional motor control.", 3),
            ("04 • Control Systems", "Intermediate", "Control", "Feedback, PID, tuning, stability and practical control loops.", "Use proportional, integral and derivative terms carefully.", 4),
            ("05 • Kinematics", "Intermediate", "Robotics Math", "Frames, transformations and forward/inverse kinematics.", "Learn how joint variables map to robot pose.", 5),
            ("06 • Computer Vision", "Intermediate", "AI & Vision", "Cameras, image processing, OpenCV and object detection.", "Start with grayscale and thresholding, then move to contours and detection.", 6),
            ("07 • ROS 2 & Navigation", "Advanced", "Software Robotics", "Nodes, topics, services, actions, TF, mapping and navigation.", "Build modular robot software with ROS 2.", 7),
        ]
        con.executemany(
            "INSERT INTO learning(title,level,category,description,content,order_no,created_at) VALUES(?,?,?,?,?,?,?)",
            [lesson + (now(),) for lesson in lessons],
        )

    if con.execute("SELECT COUNT(*) FROM quizzes").fetchone()[0] == 0:
        questions = [
            {"q": "Which component measures a physical quantity?", "options": ["Actuator", "Sensor", "Gearbox", "Frame"], "answer": 1, "explain": "Sensors convert physical conditions into usable signals."},
            {"q": "PWM is commonly used to control DC motor...", "options": ["Direction only", "Average power/speed", "Battery chemistry", "Wi-Fi password"], "answer": 1, "explain": "PWM changes average applied power using duty cycle."},
        ]
        con.execute(
            "INSERT INTO quizzes(title,topic,difficulty,description,questions_json,created_at) VALUES(?,?,?,?,?,?)",
            ("Robotics Zero → Hero", "Robotics Foundations", "Beginner", "A quick test of robotics fundamentals.", json.dumps(questions), now()),
        )

    if con.execute("SELECT COUNT(*) FROM games").fetchone()[0] == 0:
        con.executemany(
            "INSERT INTO games(title,topic,description,game_type,difficulty,created_at) VALUES(?,?,?,?,?,?)",
            [
                ("Sensor Sprint", "Sensors", "Calibrate virtual sensors and keep a robot inside a safe zone.", "sensor", "Beginner", now()),
                ("PID Pilot", "Control", "Tune Kp, Ki and Kd to keep a virtual robot centered.", "pid", "Intermediate", now()),
            ],
        )

    con.commit()
    con.close()


# Initialize on import so PythonAnywhere/WSGI also gets the schema.
init_db()


# ============================================================
# FRONTEND ROUTES — UNIQUE ENDPOINT NAMES ONLY
# ============================================================

@app.route("/")
@app.route("/index")
@app.route("/index.html")
def index_page():
    return render_template("index.html")


@app.route("/about")
@app.route("/about.html")
def about_page():
    return render_template("about.html")


@app.route("/members")
@app.route("/members.html")
def members_page():
    return render_template("members.html")


@app.route("/events")
@app.route("/events.html")
def events_page():
    return render_template("events.html")


@app.route("/learn")
@app.route("/learn.html")
def learn_page():
    return render_template("learn.html")


@app.route("/ideas")
@app.route("/ideas.html")
def ideas_page():
    return render_template("ideas.html")


@app.route("/play")
@app.route("/play.html")
@app.route("/games")
@app.route("/games.html")
def play_page():
    return render_template("play.html")


@app.route("/projects")
@app.route("/projects.html")
def projects_page():
    return render_template("projects.html")

@app.route("/admin")
@app.route("/admin.html")
@app.route("/app")
def admin_page():
    return render_template("admin.html")

@app.route("/manifest.json")
def manifest():
    return send_from_directory(BASE / "static", "manifest.json")


# ============================================================
# PUBLIC API
# ============================================================

PUBLIC_TABLES = ("members", "projects", "events", "quizzes", "games", "learning")

@app.get("/api/health")
def health():
    return jsonify({
        "success": True,
        "status": "ok",
        "service": "RCS Robotics Club",
        "database_exists": DB.exists(),
    })

@app.get("/health")
def health_alias():
    return health()

@app.get("/api/public/all")
def public_all():
    return jsonify({table: rows(table) for table in PUBLIC_TABLES})


# ============================================================
# AUTH API
# ============================================================

@app.post("/api/auth/login")
def auth_login():
    data = json_body()
    email = text_value(data, "email").lower()
    password = str(data.get("password", ""))

    if not email or not password:
        return jsonify({"success": False, "error": "Email and password are required."}), 400

    con = db()
    user = con.execute(
        "SELECT id,name,email,password,role FROM users WHERE lower(email)=lower(?) AND active=1",
        (email,),
    ).fetchone()
    con.close()

    if not user or not check_password_hash(user["password"], password):
        return jsonify({"success": False, "error": "Invalid email or password."}), 401

    session.clear()
    session["user_id"] = user["id"]
    session["name"] = user["name"]
    session["email"] = user["email"]
    session["role"] = user["role"]

    return jsonify({
        "success": True,
        "message": "Login successful.",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
        },
    })

@app.post("/api/login")
def login_alias():
    return auth_login()

@app.route("/api/auth/logout", methods=["GET", "POST"])
def auth_logout():
    session.clear()
    if request.method == "GET":
        return redirect("/admin")
    return jsonify({"success": True, "message": "Logged out successfully."})

@app.get("/api/auth/me")
def auth_me():
    if not session.get("user_id"):
        return jsonify({"authenticated": False, "success": False})
    return jsonify({
        "authenticated": True,
        "success": True,
        "user": {
            "id": session["user_id"],
            "name": session.get("name"),
            "email": session.get("email"),
            "role": session.get("role"),
        },
    })


# ============================================================
# ADMIN STATS
# ============================================================

@app.get("/api/admin/stats")
@auth_required
def admin_stats():
    con = db()
    stats = {}
    for table in PUBLIC_TABLES:
        stats[table] = con.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"]
    stats["feedback"] = con.execute("SELECT COUNT(*) AS count FROM feedback").fetchone()["count"]
    con.close()
    return jsonify({"success": True, "stats": stats})


# ============================================================
# FEEDBACK / IDEAS
# ============================================================

@app.post("/api/feedback")
def add_feedback():
    data = json_body()
    message = text_value(data, "message")
    if not message:
        return jsonify({"success": False, "error": "Message is required."}), 400

    con = db()
    cur = con.execute(
        "INSERT INTO feedback(name,email,type,title,message,status) VALUES(?,?,?,?,?,?)",
        (
            text_value(data, "name"),
            text_value(data, "email"),
            text_value(data, "type", "idea"),
            text_value(data, "title"),
            message,
            "new",
        ),
    )
    con.commit()
    con.close()
    return jsonify({"success": True, "id": cur.lastrowid, "message": "Feedback submitted successfully."}), 201


# ============================================================
# GENERIC ADMIN CRUD
# ============================================================

RESOURCE_FIELDS = {
    "members": ["name", "role", "department", "year", "bio", "image_url", "skills", "featured"],
    "projects": ["title", "category", "description", "tech", "status", "image_url", "demo_url"],
    "events": ["title", "date", "time", "venue", "description", "image_url", "registration_url"],
    "quizzes": ["title", "topic", "difficulty", "description", "questions_json"],
    "games": ["title", "topic", "description", "game_type", "difficulty"],
    "learning": ["title", "level", "category", "description", "content", "order_no"],
}

@app.get("/api/admin/<table>")
@auth_required
def admin_list(table):
    if table not in RESOURCE_FIELDS:
        return jsonify({"success": False, "error": "Unknown resource."}), 404
    return jsonify({"success": True, "items": rows(table)})

@app.post("/api/admin/<table>")
@auth_required
def admin_create(table):
    if table not in RESOURCE_FIELDS:
        return jsonify({"success": False, "error": "Unknown resource."}), 404

    data = json_body()
    fields = RESOURCE_FIELDS[table]
    values = [data.get(field, "") for field in fields]
    if table == "quizzes" and not values[4]:
        values[4] = "[]"

    con = db()
    placeholders = ",".join("?" for _ in fields)
    cur = con.execute(
        f"INSERT INTO {table} ({','.join(fields)}) VALUES ({placeholders})",
        values,
    )
    con.commit()
    item = con.execute(f"SELECT * FROM {table} WHERE id=?", (cur.lastrowid,)).fetchone()
    con.close()
    return jsonify({"success": True, "item": dict(item)}), 201

@app.put("/api/admin/<table>/<int:item_id>")
@auth_required
def admin_update(table, item_id):
    if table not in RESOURCE_FIELDS:
        return jsonify({"success": False, "error": "Unknown resource."}), 404

    data = json_body()
    fields = RESOURCE_FIELDS[table]
    sets = ", ".join(f"{field}=?" for field in fields)
    values = [data.get(field, "") for field in fields] + [item_id]

    con = db()
    cur = con.execute(f"UPDATE {table} SET {sets} WHERE id=?", values)
    con.commit()
    item = con.execute(f"SELECT * FROM {table} WHERE id=?", (item_id,)).fetchone()
    con.close()

    if cur.rowcount == 0 or item is None:
        return jsonify({"success": False, "error": "Item not found."}), 404
    return jsonify({"success": True, "item": dict(item)})

@app.delete("/api/admin/<table>/<int:item_id>")
@auth_required
def admin_delete(table, item_id):
    if table not in RESOURCE_FIELDS:
        return jsonify({"success": False, "error": "Unknown resource."}), 404

    con = db()
    cur = con.execute(f"DELETE FROM {table} WHERE id=?", (item_id,))
    con.commit()
    con.close()

    if cur.rowcount == 0:
        return jsonify({"success": False, "error": "Item not found."}), 404
    return jsonify({"success": True, "message": "Deleted successfully."})


# ============================================================
# FEEDBACK ADMIN
# ============================================================

@app.get("/api/admin/feedback")
@auth_required
def admin_feedback():
    return jsonify({"success": True, "items": rows("feedback")})

@app.put("/api/admin/feedback/<int:item_id>")
@auth_required
def update_feedback(item_id):
    status = text_value(json_body(), "status", "reviewed")
    con = db()
    cur = con.execute("UPDATE feedback SET status=? WHERE id=?", (status, item_id))
    con.commit()
    con.close()
    if cur.rowcount == 0:
        return jsonify({"success": False, "error": "Feedback not found."}), 404
    return jsonify({"success": True, "message": "Feedback updated."})


# ============================================================
# UPLOAD API
# ============================================================

@app.post("/api/admin/upload")
@auth_required
def admin_upload():
    file = request.files.get("file")
    if not file:
        return jsonify({"success": False, "error": "No file uploaded."}), 400
    try:
        url = save_upload(file)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    return jsonify({"success": True, "url": url})


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(413)
def too_large(error):
    return jsonify({"success": False, "error": "File is too large. Maximum size is 8 MB."}), 413

@app.errorhandler(404)
def not_found(error):
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "error": "API endpoint not found."}), 404
    return "Page not found.", 404


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    init_db()
    print("=" * 60)
    print("RCS ROBOTICS CLUB")
    print("=" * 60)
    print(f"Database : {DB}")
    print("Website  : http://127.0.0.1:5000/")
    print("Admin    : http://127.0.0.1:5000/admin")
    print("Health   : http://127.0.0.1:5000/api/health")
    print("Faculty  : faculty@rcs-sastra.org / RCS@2026")
    print("Member   : member@rcs-sastra.org / RCS@2026")
    print("=" * 60)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
