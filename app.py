from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session
)

import sqlite3
import os


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret-key"
)


# ============================================================
# PATHS
# ============================================================

BASE = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(
    BASE,
    "data",
    "rcs.db"
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db():

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# ADMIN LOGIN DETAILS
# ============================================================

ADMIN_USERNAME = os.environ.get(
    "ADMIN_USERNAME",
    "admin"
)

ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD",
    "change-me"
)


# ============================================================
# PUBLIC WEBSITE ROUTES
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


@app.route("/about")
def about():

    return render_template(
        "about.html"
    )


@app.route("/members")
def members():

    return render_template(
        "members.html"
    )


@app.route("/projects")
def projects():

    return render_template(
        "projects.html"
    )


@app.route("/events")
def events():

    return render_template(
        "events.html"
    )


@app.route("/learn")
def learn():

    return render_template(
        "learn.html"
    )


@app.route("/ideas")
def ideas():

    return render_template(
        "ideas.html"
    )


@app.route("/play")
def play():

    return render_template(
        "play.html"
    )


# ============================================================
# ADMIN APPLICATION PAGE
# ============================================================

@app.route("/app")
def admin_app():

    return render_template(
        "admin.html"
    )


# ============================================================
# ADMIN LOGIN
# ============================================================

@app.route(
    "/api/admin/login",
    methods=["POST"]
)
def admin_login():

    data = request.get_json(
        silent=True
    ) or {}

    username = data.get(
        "username",
        ""
    )

    password = data.get(
        "password",
        ""
    )

    if (
        username == ADMIN_USERNAME
        and password == ADMIN_PASSWORD
    ):

        session[
            "admin_logged_in"
        ] = True

        return jsonify({
            "success": True
        })

    return jsonify({
        "success": False,
        "error": "Invalid username or password"
    }), 401


# ============================================================
# CHECK ADMIN LOGIN
# ============================================================

@app.route("/api/admin/me")
def admin_me():

    return jsonify({
        "authenticated": bool(
            session.get(
                "admin_logged_in"
            )
        )
    })


# ============================================================
# ADMIN LOGOUT
# ============================================================

@app.route(
    "/api/admin/logout",
    methods=["POST"]
)
def admin_logout():

    session.pop(
        "admin_logged_in",
        None
    )

    return jsonify({
        "success": True
    })


# ============================================================
# ADMIN AUTHENTICATION HELPER
# ============================================================

def admin_required():

    if not session.get(
        "admin_logged_in"
    ):

        return jsonify({
            "success": False,
            "error": "Unauthorized"
        }), 401

    return None


# ============================================================
# ADMIN DASHBOARD STATISTICS
# ============================================================

@app.route("/api/admin/stats")
def admin_stats():

    auth = admin_required()

    if auth:
        return auth

    conn = get_db()

    cursor = conn.cursor()

    result = {}

    tables = [
        "members",
        "projects",
        "events",
        "learning",
        "quizzes",
        "games",
        "feedback"
    ]

    for table in tables:

        try:

            cursor.execute(
                f"SELECT COUNT(*) FROM {table}"
            )

            result[table] = (
                cursor.fetchone()[0]
            )

        except sqlite3.Error:

            result[table] = 0

    conn.close()

    return jsonify(result)


# ============================================================
# ADMIN TABLES
# ============================================================

ADMIN_TABLES = {
    "members",
    "projects",
    "events",
    "learning",
    "quizzes",
    "games",
    "feedback"
}


# ============================================================
# GET ADMIN TABLE DATA
# ============================================================

@app.route(
    "/api/admin/<table>",
    methods=["GET"]
)
def admin_get_table(table):

    auth = admin_required()

    if auth:
        return auth

    if table not in ADMIN_TABLES:

        return jsonify({
            "success": False,
            "error": "Invalid table"
        }), 404

    conn = get_db()

    try:

        rows = conn.execute(
            f"SELECT * FROM {table}"
        ).fetchall()

        result = [
            dict(row)
            for row in rows
        ]

    except sqlite3.Error as error:

        conn.close()

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500

    conn.close()

    return jsonify(result)


# ============================================================
# WEBSITE → IDEAS / FEEDBACK
# ============================================================

@app.route(
    "/api/feedback",
    methods=["POST"]
)
def add_feedback():

    data = request.get_json(
        silent=True
    ) or {}

    name = data.get(
        "name",
        ""
    )

    email = data.get(
        "email",
        ""
    )

    idea_type = data.get(
        "type",
        ""
    )

    title = data.get(
        "title",
        ""
    )

    message = data.get(
        "message",
        ""
    )

    if not title or not message:

        return jsonify({
            "success": False,
            "error": "Idea title and message are required"
        }), 400

    conn = get_db()

    try:

        conn.execute(
            """
            INSERT INTO feedback
            (name, email, type, title, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                email,
                idea_type,
                title,
                message
            )
        )

        conn.commit()

    except sqlite3.Error as error:

        conn.rollback()

        conn.close()

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500

    conn.close()

    return jsonify({
        "success": True,
        "message": "Idea submitted successfully"
    })


# ============================================================
# ADMIN → ADD MEMBER
# ============================================================

@app.route(
    "/api/admin/members",
    methods=["POST"]
)
def admin_add_member():

    auth = admin_required()

    if auth:
        return auth

    data = request.get_json(
        silent=True
    ) or {}

    name = data.get(
        "name",
        ""
    )

    role = data.get(
        "role",
        ""
    )

    department = data.get(
        "department",
        ""
    )

    image = data.get(
        "image",
        ""
    )

    if not name:

        return jsonify({
            "success": False,
            "error": "Name is required"
        }), 400

    conn = get_db()

    try:

        conn.execute(
            """
            INSERT INTO members
            (name, role, department, image)
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                role,
                department,
                image
            )
        )

        conn.commit()

    except sqlite3.Error as error:

        conn.rollback()

        conn.close()

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500

    conn.close()

    return jsonify({
        "success": True,
        "message": "Member added successfully"
    })


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    return jsonify({
        "status": "ok",
        "service": "RCS Robotics Club"
    })


# ============================================================
# APPLICATION START
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )
