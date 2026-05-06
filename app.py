import os
import sqlite3
from datetime import date, datetime
from functools import wraps

from flask import Flask, g, jsonify, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "team_tasks.db"))


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-change-me"),
        DATABASE=DATABASE,
    )
    if test_config:
        app.config.update(test_config)

    @app.before_request
    def ensure_database():
        init_db()

    @app.teardown_appcontext
    def close_db(error):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/auth/signup", methods=["POST"])
    def signup():
        payload = request.get_json(silent=True) or {}
        name = clean(payload.get("name"))
        email = clean(payload.get("email")).lower()
        password = payload.get("password") or ""
        role = clean(payload.get("role") or "Member")

        if not name or not email or not password:
            return error("Name, email, and password are required.", 400)
        if "@" not in email or "." not in email:
            return error("Use a valid email address.", 400)
        if len(password) < 6:
            return error("Password must be at least 6 characters.", 400)
        if role not in ("Admin", "Member"):
            return error("Role must be Admin or Member.", 400)

        try:
            cursor = get_db().execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (name, email, generate_password_hash(password), role),
            )
            get_db().commit()
        except sqlite3.IntegrityError:
            return error("An account with that email already exists.", 409)

        user = get_user_by_id(cursor.lastrowid)
        session["user_id"] = user["id"]
        return jsonify({"user": public_user(user)}), 201

    @app.route("/api/auth/login", methods=["POST"])
    def login():
        payload = request.get_json(silent=True) or {}
        email = clean(payload.get("email")).lower()
        password = payload.get("password") or ""
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            return error("Invalid email or password.", 401)
        session["user_id"] = user["id"]
        return jsonify({"user": public_user(user)})

    @app.route("/api/auth/logout", methods=["POST"])
    def logout():
        session.clear()
        return jsonify({"message": "Logged out"})

    @app.route("/api/me", methods=["GET"])
    @login_required
    def me():
        return jsonify({"user": public_user(current_user())})

    @app.route("/api/users", methods=["GET"])
    @login_required
    def users():
        rows = get_db().execute(
            "SELECT id, name, email, role, created_at FROM users ORDER BY name"
        ).fetchall()
        return jsonify({"users": [dict(row) for row in rows]})

    @app.route("/api/projects", methods=["GET"])
    @login_required
    def projects():
        user = current_user()
        if user["role"] == "Admin":
            rows = get_db().execute(
                """
                SELECT p.*, u.name AS owner_name,
                       COUNT(DISTINCT pm.user_id) AS member_count,
                       COUNT(DISTINCT t.id) AS task_count
                FROM projects p
                JOIN users u ON u.id = p.owner_id
                LEFT JOIN project_members pm ON pm.project_id = p.id
                LEFT JOIN tasks t ON t.project_id = p.id
                GROUP BY p.id
                ORDER BY p.created_at DESC
                """
            ).fetchall()
        else:
            rows = get_db().execute(
                """
                SELECT p.*, u.name AS owner_name,
                       COUNT(DISTINCT pm2.user_id) AS member_count,
                       COUNT(DISTINCT t.id) AS task_count
                FROM projects p
                JOIN users u ON u.id = p.owner_id
                JOIN project_members pm ON pm.project_id = p.id AND pm.user_id = ?
                LEFT JOIN project_members pm2 ON pm2.project_id = p.id
                LEFT JOIN tasks t ON t.project_id = p.id
                GROUP BY p.id
                ORDER BY p.created_at DESC
                """,
                (user["id"],),
            ).fetchall()
        return jsonify({"projects": [dict(row) for row in rows]})

    @app.route("/api/projects", methods=["POST"])
    @login_required
    @admin_required
    def create_project():
        payload = request.get_json(silent=True) or {}
        name = clean(payload.get("name"))
        description = clean(payload.get("description"))
        member_ids = normalize_ids(payload.get("member_ids", []))
        if not name:
            return error("Project name is required.", 400)

        db = get_db()
        cursor = db.execute(
            "INSERT INTO projects (name, description, owner_id) VALUES (?, ?, ?)",
            (name, description, current_user()["id"]),
        )
        project_id = cursor.lastrowid
        member_ids.add(current_user()["id"])
        add_project_members(project_id, member_ids)
        db.commit()
        return jsonify({"project": get_project(project_id)}), 201

    @app.route("/api/projects/<int:project_id>", methods=["GET"])
    @login_required
    def project_detail(project_id):
        denied = require_project_access(project_id)
        if denied:
            return denied
        project = get_project(project_id)
        if project is None:
            return error("Project not found.", 404)
        members = get_db().execute(
            """
            SELECT u.id, u.name, u.email, u.role
            FROM project_members pm
            JOIN users u ON u.id = pm.user_id
            WHERE pm.project_id = ?
            ORDER BY u.name
            """,
            (project_id,),
        ).fetchall()
        return jsonify({"project": project, "members": [dict(row) for row in members]})

    @app.route("/api/projects/<int:project_id>/members", methods=["PUT"])
    @login_required
    @admin_required
    def update_project_members(project_id):
        if get_project(project_id) is None:
            return error("Project not found.", 404)
        member_ids = normalize_ids((request.get_json(silent=True) or {}).get("member_ids", []))
        member_ids.add(current_user()["id"])
        db = get_db()
        db.execute("DELETE FROM project_members WHERE project_id = ?", (project_id,))
        add_project_members(project_id, member_ids)
        db.commit()
        return project_detail(project_id)

    @app.route("/api/tasks", methods=["GET"])
    @login_required
    def tasks():
        user = current_user()
        params = []
        where = []
        if user["role"] != "Admin":
            where.append(
                "(t.assignee_id = ? OR EXISTS (SELECT 1 FROM project_members pm WHERE pm.project_id = t.project_id AND pm.user_id = ?))"
            )
            params.extend([user["id"], user["id"]])
        project_id = request.args.get("project_id", type=int)
        if project_id:
            where.append("t.project_id = ?")
            params.append(project_id)
        sql = task_query()
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY CASE t.status WHEN 'Todo' THEN 1 WHEN 'In Progress' THEN 2 ELSE 3 END, t.due_date"
        rows = get_db().execute(sql, params).fetchall()
        return jsonify({"tasks": [serialize_task(row) for row in rows]})

    @app.route("/api/tasks", methods=["POST"])
    @login_required
    def create_task():
        payload = request.get_json(silent=True) or {}
        title = clean(payload.get("title"))
        project_id = payload.get("project_id")
        assignee_id = payload.get("assignee_id")
        status = clean(payload.get("status") or "Todo")
        due_date = clean(payload.get("due_date"))
        description = clean(payload.get("description"))

        validation = validate_task_payload(title, project_id, assignee_id, status, due_date)
        if validation:
            return validation
        if current_user()["role"] != "Admin" and int(assignee_id) != current_user()["id"]:
            return error("Members can only create tasks assigned to themselves.", 403)
        denied = require_project_access(project_id)
        if denied:
            return denied

        cursor = get_db().execute(
            """
            INSERT INTO tasks (project_id, title, description, assignee_id, status, due_date, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (project_id, title, description, assignee_id, status, due_date, current_user()["id"]),
        )
        get_db().commit()
        return jsonify({"task": get_task(cursor.lastrowid)}), 201

    @app.route("/api/tasks/<int:task_id>", methods=["PATCH"])
    @login_required
    def update_task(task_id):
        task = get_task(task_id)
        if task is None:
            return error("Task not found.", 404)
        user = current_user()
        if user["role"] != "Admin" and task["assignee_id"] != user["id"]:
            return error("You can only update your assigned tasks.", 403)

        payload = request.get_json(silent=True) or {}
        status = clean(payload.get("status") or task["status"])
        title = clean(payload.get("title") or task["title"])
        description = clean(payload.get("description") if payload.get("description") is not None else task["description"])
        assignee_id = payload.get("assignee_id", task["assignee_id"])
        due_date = clean(payload.get("due_date") or task["due_date"])

        if user["role"] != "Admin":
            assignee_id = task["assignee_id"]
            title = task["title"]
            description = task["description"]
            due_date = task["due_date"]

        validation = validate_task_payload(title, task["project_id"], assignee_id, status, due_date)
        if validation:
            return validation

        get_db().execute(
            """
            UPDATE tasks
            SET title = ?, description = ?, assignee_id = ?, status = ?, due_date = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (title, description, assignee_id, status, due_date, task_id),
        )
        get_db().commit()
        return jsonify({"task": get_task(task_id)})

    @app.route("/api/dashboard", methods=["GET"])
    @login_required
    def dashboard():
        user = current_user()
        params = []
        where = []
        if user["role"] != "Admin":
            where.append("t.assignee_id = ?")
            params.append(user["id"])
        base = " FROM tasks t "
        if where:
            base += " WHERE " + " AND ".join(where)

        db = get_db()
        total = db.execute("SELECT COUNT(*) AS count" + base, params).fetchone()["count"]
        overdue = db.execute(
            "SELECT COUNT(*) AS count" + base + (" AND" if where else " WHERE") + " t.status != 'Done' AND t.due_date < ?",
            params + [date.today().isoformat()],
        ).fetchone()["count"]
        by_status = db.execute(
            "SELECT t.status, COUNT(*) AS count" + base + " GROUP BY t.status",
            params,
        ).fetchall()
        upcoming = db.execute(
            task_query()
            + (" WHERE " + " AND ".join(where) + " AND" if where else " WHERE")
            + " t.status != 'Done' ORDER BY t.due_date LIMIT 6",
            params,
        ).fetchall()
        return jsonify(
            {
                "total": total,
                "overdue": overdue,
                "by_status": {row["status"]: row["count"] for row in by_status},
                "upcoming": [serialize_task(row) for row in upcoming],
            }
        )

    return app


def clean(value):
    return str(value or "").strip()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app_config("DATABASE"))
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def current_app_config(key):
    from flask import current_app

    return current_app.config[key]


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('Admin', 'Member')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            owner_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(owner_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS project_members (
            project_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            PRIMARY KEY(project_id, user_id),
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            assignee_id INTEGER NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Todo', 'In Progress', 'Done')),
            due_date TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(assignee_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )
    db.commit()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session or current_user() is None:
            return error("Authentication required.", 401)
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user()["role"] != "Admin":
            return error("Admin access required.", 403)
        return view(*args, **kwargs)

    return wrapped


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_user_by_id(user_id)


def get_user_by_id(user_id):
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def public_user(user):
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "created_at": user["created_at"],
    }


def error(message, status):
    return jsonify({"error": message}), status


def normalize_ids(values):
    ids = set()
    for value in values or []:
        try:
            ids.add(int(value))
        except (TypeError, ValueError):
            continue
    return ids


def add_project_members(project_id, member_ids):
    db = get_db()
    for member_id in member_ids:
        if get_user_by_id(member_id):
            db.execute(
                "INSERT OR IGNORE INTO project_members (project_id, user_id) VALUES (?, ?)",
                (project_id, member_id),
            )


def get_project(project_id):
    row = get_db().execute(
        """
        SELECT p.*, u.name AS owner_name
        FROM projects p
        JOIN users u ON u.id = p.owner_id
        WHERE p.id = ?
        """,
        (project_id,),
    ).fetchone()
    return dict(row) if row else None


def require_project_access(project_id):
    project = get_project(project_id)
    if project is None:
        return error("Project not found.", 404)
    user = current_user()
    if user["role"] == "Admin":
        return None
    membership = get_db().execute(
        "SELECT 1 FROM project_members WHERE project_id = ? AND user_id = ?",
        (project_id, user["id"]),
    ).fetchone()
    if membership is None:
        return error("Project access denied.", 403)
    return None


def validate_task_payload(title, project_id, assignee_id, status, due_date):
    if not title or not project_id or not assignee_id or not due_date:
        return error("Title, project, assignee, and due date are required.", 400)
    if status not in ("Todo", "In Progress", "Done"):
        return error("Status must be Todo, In Progress, or Done.", 400)
    try:
        datetime.strptime(due_date, "%Y-%m-%d")
    except ValueError:
        return error("Due date must use YYYY-MM-DD format.", 400)
    if get_project(project_id) is None:
        return error("Project not found.", 404)
    if get_user_by_id(assignee_id) is None:
        return error("Assignee not found.", 404)
    membership = get_db().execute(
        "SELECT 1 FROM project_members WHERE project_id = ? AND user_id = ?",
        (project_id, assignee_id),
    ).fetchone()
    if membership is None:
        return error("Assignee must be a project member.", 400)
    return None


def task_query():
    return """
        SELECT t.*, p.name AS project_name, u.name AS assignee_name, c.name AS creator_name
        FROM tasks t
        JOIN projects p ON p.id = t.project_id
        JOIN users u ON u.id = t.assignee_id
        JOIN users c ON c.id = t.created_by
    """


def get_task(task_id):
    row = get_db().execute(task_query() + " WHERE t.id = ?", (task_id,)).fetchone()
    return serialize_task(row) if row else None


def serialize_task(row):
    task = dict(row)
    task["is_overdue"] = task["status"] != "Done" and task["due_date"] < date.today().isoformat()
    return task


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
