from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for
)

import sqlite3
import os
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret-key"
)
BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "src_rcs.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

ADMIN_USERNAME = os.environ.get(
    "ADMIN_USERNAME",
    "admin"
)

ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD",
    "change-me"
)
@app.route("/api/admin/login", methods=["POST"])
def admin_login():

    data = request.get_json(silent=True) or {}

    username = data.get("username", "")
    password = data.get("password", "")

    if (
        username == ADMIN_USERNAME
        and password == ADMIN_PASSWORD
    ):

        session["admin_logged_in"] = True

        return jsonify({
            "success": True
        })

    return jsonify({
        "error": "Invalid username or password"
    }), 401

@app.route("/api/admin/me")
def admin_me():

    return jsonify({
        "authenticated":
            bool(session.get("admin_logged_in"))
    })

@app.route("/api/admin/logout", methods=["POST"])
def admin_logout():

    session.pop("admin_logged_in", None)

    return jsonify({
        "success": True
    })

def admin_required():

    if not session.get("admin_logged_in"):
        return jsonify({
            "error": "Unauthorized"
        }), 401

    return None
    auth = admin_required()
    if auth:
        return auth


@app.route("/app")
def admin_app():

    return render_template("admin.html")


@app.route("/api/admin/stats")
def admin_stats():

    auth = admin_required()

    if auth:
        return auth

    conn = get_db()
    cur = conn.cursor()

    result = {}

    for table in [
        "members",
        "projects",
        "events",
        "quizzes"
    ]:

        try:

            cur.execute(
                f"SELECT COUNT(*) FROM {table}"
            )

            result[table] = cur.fetchone()[0]

        except sqlite3.Error:

            result[table] = 0

    conn.close()

    return jsonify(result)

ADMIN_TABLES = {
    "members",
    "projects",
    "events",
    "learning",
    "quizzes",
    "games",
    "ideas"
}
@app.route("/api/admin/<table>")
def admin_get_table(table):

    auth = admin_required()

    if auth:
        return auth

    if table not in ADMIN_TABLES:
        return jsonify({
            "error": "Invalid table"
        }), 404

    conn = get_db()

    rows = conn.execute(
        f"SELECT * FROM {table}"
    ).fetchall()

    conn.close()

    return jsonify([
        dict(row)
        for row in rows
    ])

@app.route("/api/admin/members", methods=["POST"])
def admin_add_member():

    auth = admin_required()

    if auth:
        return auth

    data = request.get_json(silent=True) or {}

    conn = get_db()

    conn.execute("""
        INSERT INTO members
        (name, role, department, image)
        VALUES (?, ?, ?, ?)
    """, (
        data.get("name"),
        data.get("role"),
        data.get("department"),
        data.get("image")
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True
    })

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/members")
def members_page():
    return render_template("members.html")


@app.route("/projects")
def projects_page():
    return render_template("projects.html")


@app.route("/events")
def events_page():
    return render_template("events.html")


@app.route("/learning")
def learning_page():
    return render_template("learning.html")


@app.route("/quizzes")
def quizzes_page():
    return render_template("quizzes.html")


@app.route("/games")
def games_page():
    return render_template("games.html")


@app.route("/ideas")
def ideas_page():
    return render_template("ideas.html")

