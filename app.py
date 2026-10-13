import json
import os
from datetime import date, time
from urllib.parse import quote
from functools import wraps
from pathlib import Path
from flask import Flask, jsonify, request, session, render_template, send_from_directory, redirect
import config
from dotenv import load_dotenv
from supabase import Client, create_client
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env")
DATABASE_URL = os.getenv("DATABASE_URL")
# Render supplies the database and Supabase credentials through environment variables.
UPLOADS = BASE / "static" / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "rcs-dev-secret-change-me")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
ALLOWED = {"png","jpg","jpeg","webp","gif"}
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client | None = (
    create_client(SUPABASE_URL, SUPABASE_KEY)
    if SUPABASE_URL and SUPABASE_KEY else None
)

class CompatRow(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            return tuple(self.values())[key]
        return super().__getitem__(key)

class PostgresConnection:
    def __init__(self, url):
        import psycopg
        if "sslmode=" not in url:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}sslmode=require"
        self.con = psycopg.connect(url)

    def execute(self, query, params=()):
        cursor = self.con.cursor()
        cursor.execute(query.replace("?", "%s"), params)
        return PostgresCursor(cursor)

    def executemany(self, query, params):
        self.con.cursor().executemany(query.replace("?", "%s"), params)

    def commit(self):
        self.con.commit()

    def close(self):
        self.con.close()

class PostgresCursor:
    def __init__(self, cursor):
        self.cursor = cursor

    def _row(self, row):
        if row is None:
            return None
        return CompatRow({
            column.name: value.isoformat() if isinstance(value, (date, time)) else value
            for column, value in zip(self.cursor.description, row)
        })

    def fetchone(self):
        return self._row(self.cursor.fetchone())

    def fetchall(self):
        return [self._row(row) for row in self.cursor.fetchall()]

    @property
    def lastrowid(self):
        row = self.fetchone()
        return row[0] if row else None

def db():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is required. Configure the Supabase PostgreSQL "
            "connection string in .env or the deployment environment."
        )
    return PostgresConnection(DATABASE_URL)

def init_db():
    con = db()
    id_type = "SERIAL"
    schema = """
    CREATE TABLE IF NOT EXISTS users(
            id {id_type} PRIMARY KEY, name TEXT NOT NULL,
      email TEXT UNIQUE NOT NULL, password TEXT NOT NULL,
      role TEXT NOT NULL CHECK(role IN ('faculty','member')), active INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS members(
            id {id_type} PRIMARY KEY, name TEXT NOT NULL, role TEXT,
      department TEXT, year TEXT, bio TEXT, image_url TEXT, skills TEXT, featured BOOLEAN DEFAULT FALSE
    );
    CREATE TABLE IF NOT EXISTS projects(
            id {id_type} PRIMARY KEY, title TEXT NOT NULL, category TEXT,
      description TEXT, tech TEXT, status TEXT, image_url TEXT, demo_url TEXT
    );
    CREATE TABLE IF NOT EXISTS events(
            id {id_type} PRIMARY KEY, title TEXT NOT NULL, date TEXT,
      time TEXT, venue TEXT, description TEXT, image_url TEXT, registration_url TEXT
    );
    CREATE TABLE IF NOT EXISTS quizzes(
            id {id_type} PRIMARY KEY, title TEXT NOT NULL, topic TEXT,
      difficulty TEXT, description TEXT, questions_json TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS games(
            id {id_type} PRIMARY KEY, title TEXT NOT NULL, topic TEXT,
      description TEXT, game_type TEXT, difficulty TEXT
    );
    CREATE TABLE IF NOT EXISTS learning(
            id {id_type} PRIMARY KEY, title TEXT NOT NULL, level TEXT,
      category TEXT, description TEXT, content TEXT, order_no INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS feedback(
            id {id_type} PRIMARY KEY, name TEXT, email TEXT, type TEXT,
      title TEXT, message TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, status TEXT DEFAULT 'new'
    );
    """.format(id_type=id_type)
    for statement in schema.split(";"):
        if statement.strip():
            con.execute(statement)
    # Demo accounts — insert only when the email does not already exist.
    demo_users = [
        ("RCS Faculty", "faculty@rcs-sastra.org", "RCS@2026", "faculty"),
        ("RCS Member", "member@rcs-sastra.org", "RCS@2026", "member"),
    ]
    for name, email, password, role in demo_users:
        con.execute(
            """
            INSERT INTO users(name, email, password, role)
            SELECT ?, ?, ?, ?
            WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = ?)
            """,
            (name, email, generate_password_hash(password), role, email),
        )
    if con.execute("SELECT COUNT(*) FROM members").fetchone()[0] == 0:
        members = [
          ("RCS Core Team","Club Lead","Electronics & Communication Engineering","3rd Year","Leads builds, workshops and competitions.","","Embedded Systems, Robotics, ROS",True),
          ("RCS Core Team","Technical Lead","Electrical & Electronics Engineering","3rd Year","Owns robot architecture, electronics and integration.","","Arduino, ESP32, PCB, Control",True),
          ("RCS Core Team","AI & Vision Lead","Computer Science & Engineering","3rd Year","Builds perception, computer vision and ML experiments.","","Python, OpenCV, ML",True),
          ("RCS Volunteer","Mechanical Team","Mechanical Engineering","2nd Year","CAD, fabrication and mechanism design enthusiast.","","CAD, 3D Printing, Mechanisms",False)
        ]
        con.executemany("INSERT INTO members(name,role,department,year,bio,image_url,skills,featured) VALUES(?,?,?,?,?,?,?,?)",members)
    if con.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 0:
        projects=[
          ("Autonomous Line Follower","Autonomy","Fast, robust line-following robot with PID control and sensor fusion.","ESP32, IR array, PID","Prototype","", ""),
          ("Predictive Conveyor Intelligence","Industrial Robotics","Sensor + vision pipeline for detecting belt-joint wear and abnormal motion.","ESP32, Python, OpenCV, ML","In Progress","", ""),
          ("3-DOF Robotic Arm","Manipulation","Interactive arm controlled through keyboard/serial commands with forward kinematics.","Arduino, Servo, MATLAB","Prototype","", "")
        ]
        con.executemany("INSERT INTO projects(title,category,description,tech,status,image_url,demo_url) VALUES(?,?,?,?,?,?,?)",projects)
    if con.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0:
        events=[
          ("RCS Robotics Induction","2026-09-15","17:00","SASTRA Campus","Meet the team, see our robots and choose a technical track.","",""),
          ("Arduino + Sensors Bootcamp","2026-09-22","16:30","Innovation Lab","Hands-on workshop covering GPIO, PWM, sensors and motor control.","",""),
          ("RCS Robot Race","2026-10-10","10:00","Main Block Arena","An exciting beginner-friendly autonomous robot challenge.","","")
        ]
        con.executemany("INSERT INTO events(title,date,time,venue,description,image_url,registration_url) VALUES(?,?,?,?,?,?,?)",events)
    if con.execute("SELECT COUNT(*) FROM learning").fetchone()[0] == 0:
        lessons=[
          ("01 • Robotics Foundations","Beginner","Foundations","What is a robot? Understand sensors, actuators, controllers, feedback, coordinate frames and the basic robot loop.","A robot senses the world, decides what to do, and acts. Start with GPIO, voltage/current, motors, encoders, sensor calibration and closed-loop thinking.",1),
          ("02 • Electronics & Embedded","Beginner","Electronics","Learn microcontrollers, digital/analog I/O, PWM, ADC, interrupts, serial protocols and power design.","Build on Arduino/ESP32. Learn pull-ups, debouncing, ADC scaling, PWM motor control, UART, I2C and SPI.",2),
          ("03 • Motors & Motion","Beginner","Actuation","DC motors, servos, steppers, encoders, H-bridges and drivetrain basics.","Understand torque, speed, gearing and why an H-bridge is needed for bidirectional DC motor control.",3),
          ("04 • Control Systems","Intermediate","Control","Feedback, PID, tuning, stability, response and practical control loops.","For a line follower, proportional error turns into steering correction. Add integral and derivative terms carefully.",4),
          ("05 • Kinematics","Intermediate","Robotics Math","Frames, homogeneous transforms, forward and inverse kinematics for robot arms.","Learn how joint angles map to end-effector pose and how transformations chain together.",5),
          ("06 • Computer Vision","Intermediate","AI & Vision","Cameras, image processing, OpenCV, segmentation, feature extraction and object detection.","Start with grayscale and thresholding, then move to contours, calibration and neural-network detection.",6),
          ("07 • ROS 2 & Navigation","Advanced","Software Robotics","Nodes, topics, services, actions, TF, sensors, mapping and navigation.","Use ROS 2 to connect robot components into a modular software system. Learn message flow and coordinate transforms.",7),
          ("08 • SLAM & Autonomy","Advanced","Autonomy","Localization, mapping, path planning and autonomous decision making.","Explore occupancy grids, localization uncertainty, A*/Dijkstra and behavior-based autonomy.",8),
          ("09 • Industrial Robotics","Advanced","Industrial","PLC basics, safety, conveyors, predictive maintenance, robot cells and digital twins.","Bridge student prototypes to real factory systems: sensing, edge computing, anomaly detection and safe actuation.",9)
        ]
        con.executemany("INSERT INTO learning(title,level,category,description,content,order_no) VALUES(?,?,?,?,?,?)",lessons)
    if con.execute("SELECT COUNT(*) FROM quizzes").fetchone()[0] == 0:
        q1=[
          {"q":"Which component measures a physical quantity such as distance or temperature?","options":["Actuator","Sensor","Gearbox","Frame"],"answer":1,"explain":"Sensors convert physical conditions into usable signals."},
          {"q":"PWM is commonly used to control DC motor...","options":["Direction only","Average power/speed","Battery chemistry","Wi-Fi password"],"answer":1,"explain":"PWM varies average applied power by changing duty cycle."},
          {"q":"What does PID use as its input?","options":["Only voltage","Control error","Motor color","Robot name"],"answer":1,"explain":"PID acts on the difference between target and measured output."}
        ]
        q2=[
          {"q":"In forward kinematics, you calculate...","options":["Joint angles from pose","End-effector pose from joint variables","Battery life from Wi-Fi","Camera pixels from RAM"],"answer":1,"explain":"Forward kinematics maps known joint variables to the robot pose."},
          {"q":"Which ROS 2 concept is primarily used for continuous data streams?","options":["Topic","Action only","Password","Folder"],"answer":0,"explain":"Topics publish/subscribe to streams such as sensor data."}
        ]
        con.execute("INSERT INTO quizzes(title,topic,difficulty,description,questions_json) VALUES(?,?,?,?,?)",
                    ("Robotics Zero → Hero","Robotics Foundations","Beginner","A quick test of the fundamentals.",json.dumps(q1)))
        con.execute("INSERT INTO quizzes(title,topic,difficulty,description,questions_json) VALUES(?,?,?,?,?)",
                    ("Robot Brain Challenge","Kinematics + ROS 2","Intermediate","Test your understanding of kinematics and robotics software.",json.dumps(q2)))
    if con.execute("SELECT COUNT(*) FROM games").fetchone()[0] == 0:
        games=[
          ("Sensor Sprint","Sensors","Calibrate virtual sensors and keep a robot inside a safe zone.","sensor","Beginner"),
          ("PID Pilot","Control","Tune Kp, Ki and Kd to keep a virtual robot centered on a line.","pid","Intermediate"),
          ("Warehouse Navigator","Autonomy","Plan a collision-free route through a mini warehouse grid.","path","Advanced")
        ]
        con.executemany("INSERT INTO games(title,topic,description,game_type,difficulty) VALUES(?,?,?,?,?)",games)
    con.commit(); con.close()

def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error":"Authentication required"}),401
        return fn(*args, **kwargs)
    return wrapper

def faculty_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get("role") != "faculty":
            return jsonify({"error":"Faculty access required"}),403
        return fn(*args, **kwargs)
    return wrapper

def rows(table):
    con=db(); data=[dict(r) for r in con.execute(f"SELECT * FROM {table}").fetchall()]; con.close(); return data

@app.route("/")
def home():
    return render_template("index.html", config=config)

@app.route("/app")
def admin_app(): return render_template("admin.html", config=config)

@app.route("/login")
def login_page(): return render_template("admin.html", config=config)

@app.route("/feedback")
def feedback_page():
    msg = request.args.get("message", "")
    if msg:
        return redirect(f"/?message={quote(msg)}#feedback")
    return redirect("/#feedback")

@app.route("/manifest.json")
def manifest(): return send_from_directory(BASE/"static","manifest.json")

@app.get("/api/public/all")
def public_all():
    data = {t: rows(t) for t in ["members", "projects", "events", "quizzes", "games", "learning"]}
    data["goals"] = config.GOALS
    data["club"] = {
        "name": config.CLUB_NAME,
        "tagline": config.CLUB_TAGLINE,
        "description": config.CLUB_DESCRIPTION
    }
    return jsonify(data)

@app.post("/api/auth/login")
def login():
    body=request.get_json(silent=True) or {}
    con=db(); u=con.execute("SELECT * FROM users WHERE email=? AND active=TRUE",(body.get("email","").strip().lower(),)).fetchone(); con.close()
    if not u or not check_password_hash(u["password"],body.get("password","")):
        return jsonify({"error":"Invalid email or password"}),401
    session.clear(); session["user_id"]=u["id"]; session["name"]=u["name"]; session["role"]=u["role"]; session["email"]=u["email"]
    return jsonify({"name":u["name"],"email":u["email"],"role":u["role"]})

@app.route("/api/auth/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    if request.method == "GET":
        return redirect("/app")
    return jsonify({"ok":True})

@app.get("/api/auth/me")
def me():
    if not session.get("user_id"): return jsonify({"authenticated":False})
    return jsonify({"authenticated":True,"name":session["name"],"email":session["email"],"role":session["role"]})

@app.post("/api/feedback")
def add_feedback():
    b=request.get_json(silent=True) or {}
    if not b.get("message"): return jsonify({"error":"Message is required"}),400
    con=db(); con.execute("INSERT INTO feedback(name,email,type,title,message) VALUES(?,?,?,?,?)",
                           (b.get("name",""),b.get("email",""),b.get("type","idea"),b.get("title",""),b["message"]))
    con.commit(); con.close(); return jsonify({"ok":True})

RESOURCE_FIELDS={
 "members":["name","role","department","year","bio","image_url","skills","featured"],
 "projects":["title","category","description","tech","status","image_url","demo_url"],
 "events":["title","date","time","venue","description","image_url","registration_url"],
 "quizzes":["title","topic","difficulty","description","questions_json"],
 "games":["title","topic","description","game_type","difficulty"],
 "learning":["title","level","category","description","content","order_no"]
}
@auth_required
def crud_list(table):
    return jsonify(rows(table))

@app.get("/api/admin/<table>")
@auth_required
def admin_list(table):
    if table not in RESOURCE_FIELDS: return jsonify({"error":"Unknown resource"}),404
    return crud_list(table)

@app.post("/api/admin/<table>")
@auth_required
def admin_create(table):
    if table not in RESOURCE_FIELDS: return jsonify({"error":"Unknown resource"}),404
    b=request.get_json(silent=True) or {}
    fields=RESOURCE_FIELDS[table]
    vals=[b.get(f,"") for f in fields]
    if table=="quizzes" and not b.get("questions_json"): vals[4]="[]"
    con=db()
    insert_sql=f"INSERT INTO {table} ({','.join(fields)}) VALUES ({','.join(['?']*len(fields))})"
    insert_sql += " RETURNING id"
    cur=con.execute(insert_sql,vals)
    con.commit(); item=dict(con.execute(f"SELECT * FROM {table} WHERE id=?",(cur.lastrowid,)).fetchone()); con.close()
    return jsonify(item),201

@app.put("/api/admin/<table>/<int:item_id>")
@auth_required
def admin_update(table,item_id):
    if table not in RESOURCE_FIELDS: return jsonify({"error":"Unknown resource"}),404
    b=request.get_json(silent=True) or {}; fields=RESOURCE_FIELDS[table]
    sets=", ".join([f"{f}=?" for f in fields]); vals=[b.get(f,"") for f in fields]+[item_id]
    con=db(); con.execute(f"UPDATE {table} SET {sets} WHERE id=?",vals); con.commit()
    item=con.execute(f"SELECT * FROM {table} WHERE id=?",(item_id,)).fetchone(); con.close()
    if not item: return jsonify({"error":"Not found"}),404
    return jsonify(dict(item))

@app.delete("/api/admin/<table>/<int:item_id>")
@auth_required
def admin_delete(table,item_id):
    if table not in RESOURCE_FIELDS: return jsonify({"error":"Unknown resource"}),404
    con=db(); con.execute(f"DELETE FROM {table} WHERE id=?", (item_id,)); con.commit(); con.close()
    return jsonify({"ok":True})

@app.get("/api/admin/feedback")
@auth_required
def admin_feedback(): return jsonify(rows("feedback"))

@app.put("/api/admin/feedback/<int:item_id>")
@auth_required
def feedback_status(item_id):
    b=request.get_json(silent=True) or {}; status=b.get("status","reviewed")
    con=db(); con.execute("UPDATE feedback SET status=? WHERE id=?",(status,item_id)); con.commit(); con.close()
    return jsonify({"ok":True})

@app.post("/api/admin/upload")
@auth_required
def upload():
    f=request.files.get("file")
    if not f or not f.filename: return jsonify({"error":"No file"}),400
    ext=f.filename.rsplit(".",1)[-1].lower() if "." in f.filename else ""
    if ext not in ALLOWED: return jsonify({"error":"Allowed: png, jpg, jpeg, webp, gif"}),400
    name=secure_filename(f.filename)
    stem, suffix=os.path.splitext(name)
    path=UPLOADS/name
    i=1
    while path.exists():
        path=UPLOADS/f"{stem}-{i}{suffix}"; i+=1
    f.save(path)
    return jsonify({"url":"/static/uploads/"+path.name})

@app.get("/health")
def health():
    try:
        con = db()
        con.execute("SELECT 1").fetchone()
        con.close()
    except Exception:
        app.logger.exception("Supabase database health check failed")
        return jsonify({"status":"error","service":"RCS Robotics Club","database":"unavailable"}), 503
    return jsonify({"status":"ok","service":"RCS Robotics Club","database":"supabase"})

@app.get("/api/supabase/todos")
def supabase_todos():
    if supabase is None:
        return jsonify({"error":"SUPABASE_URL and SUPABASE_KEY are not configured"}), 503
    try:
        return jsonify(supabase.table("todos").select("*").execute().data)
    except Exception as error:
        app.logger.exception("Supabase todos query failed")
        if getattr(error, "code", None) == "PGRST205":
            return jsonify({"error":"The Supabase todos table is missing. Run migrations/001_create_todos.sql in the Supabase SQL Editor."}), 503
        return jsonify({"error":"Unable to load todos from Supabase"}), 502

@app.get("/supabase")
def supabase_page():
    if supabase is None:
        return "<h1>Supabase is not configured</h1>", 503
    try:
        todos = supabase.table("todos").select("*").execute().data
    except Exception as error:
        app.logger.exception("Supabase todos page query failed")
        if getattr(error, "code", None) == "PGRST205":
            return "<h1>Supabase todos table is missing</h1><p>Run migrations/001_create_todos.sql in the Supabase SQL Editor.</p>", 503
        return "<h1>Unable to load todos</h1>", 502
    items = "".join(f"<li>{todo.get('name', '')}</li>" for todo in todos)
    return f"<h1>Todos</h1><ul>{items}</ul>"

@app.route("/about")
def about(): return redirect("/#about")

@app.route("/members")
def members(): return redirect("/#members")

@app.route("/projects")
def projects(): return redirect("/#projects")

@app.route("/events")
def events(): return redirect("/#events")

@app.route("/learn")
def learn(): return redirect("/#resources")

@app.route("/play")
def play(): return redirect("/#play")

@app.route("/ideas")
def ideas(): return redirect("/#feedback")

init_db()

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT","5000")), debug=True)