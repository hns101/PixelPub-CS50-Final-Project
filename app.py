import os
import sqlite3
import json
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_socketio import SocketIO, emit, join_room, leave_room
from cs50 import SQL
from functools import wraps

# --- Database Initialization ---
DB_FILE = "project.db"
def initialize_database():
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user');")
    cur.execute("CREATE TABLE IF NOT EXISTS canvases (id INTEGER PRIMARY KEY, name TEXT NOT NULL, width INTEGER, height INTEGER, owner_id INTEGER, is_public BOOLEAN DEFAULT 0, is_community BOOLEAN DEFAULT 0, canvas_data TEXT, FOREIGN KEY(owner_id) REFERENCES users(id));")
    cur.execute("CREATE TABLE IF NOT EXISTS pixel_history (id INTEGER PRIMARY KEY, canvas_id INTEGER NOT NULL, x INTEGER NOT NULL, y INTEGER NOT NULL, modifier_id INTEGER NOT NULL, color TEXT NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(canvas_id) REFERENCES canvases(id), FOREIGN KEY(modifier_id) REFERENCES users(id));")
    community_canvases = [("The Garden", 48, 48), ("The City", 64, 32), ("The Ocean", 32, 64)]
    for name, width, height in community_canvases:
        cur.execute("SELECT id FROM canvases WHERE is_community = 1 AND name = ?", (name,))
        if cur.fetchone() is None:
            initial_data = [['#FFFFFF' for _ in range(width)] for _ in range(height)]
            cur.execute("INSERT INTO canvases (name, width, height, is_community, canvas_data) VALUES (?, ?, ?, ?, ?)", (name, width, height, 1, json.dumps(initial_data)))
    con.commit()
    con.close()

if not os.path.exists(DB_FILE):
    initialize_database()

db = SQL(f"sqlite:///{DB_FILE}")

# --- App Configuration ---
app = Flask(__name__)
app.config["SECRET_KEY"] = "a_super_secret_key_for_socketio"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
socketio = SocketIO(app)

# --- Helper Functions ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None: return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "admin": return apology("Admin access required", 403)
        return f(*args, **kwargs)
    return decorated_function

def apology(message, code=400):
    return render_template("apology.html", top=code, bottom=message), code

# --- Main & User Routes ---
@app.route("/")
def index():
    if session.get("user_id"): return redirect("/dashboard")
    return redirect("/login")

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    user_id = session["user_id"]
    if request.method == "POST":
        name, width, height = request.form.get("name"), int(request.form.get("width")), int(request.form.get("height"))
        if not name or not (16 <= width <= 64 and 16 <= height <= 64): return apology("Invalid canvas details", 400)
        # This line correctly creates an all-white canvas. No change needed.
        initial_data = [['#FFFFFF' for _ in range(width)] for _ in range(height)]
        db.execute("INSERT INTO canvases (name, width, height, owner_id, canvas_data) VALUES (?, ?, ?, ?, ?)", name, width, height, user_id, json.dumps(initial_data))
        flash("Canvas created successfully!")
        return redirect("/dashboard")
    else:
        my_canvases = db.execute("SELECT * FROM canvases WHERE owner_id = ?", user_id)
        return render_template("dashboard.html", canvases=my_canvases)

# Other routes remain the same...
@app.route("/gallery")
def gallery():
    public_canvases = db.execute("SELECT c.*, u.username FROM canvases c JOIN users u ON c.owner_id = u.id WHERE c.is_public = 1")
    return render_template("gallery.html", canvases=public_canvases)

@app.route("/community")
def community():
    community_canvases = db.execute("SELECT * FROM canvases WHERE is_community = 1")
    return render_template("community.html", canvases=community_canvases)

@app.route("/canvas/<int:canvas_id>")
@login_required
def canvas(canvas_id):
    canvas_info = db.execute("SELECT * FROM canvases WHERE id = ?", canvas_id)
    if not canvas_info: return apology("Canvas not found", 404)
    canvas_info = canvas_info[0]
    is_owner = (canvas_info["owner_id"] == session["user_id"])
    is_admin = session.get("role") == "admin"
    can_view = is_owner or canvas_info["is_public"] or canvas_info["is_community"] or is_admin
    if not can_view: return apology("You do not have permission to view this canvas", 403)
    return render_template("canvas.html", canvas_info=canvas_info, is_owner=is_owner, is_admin=is_admin)

@app.route("/toggle_public/<int:canvas_id>", methods=["POST"])
@login_required
def toggle_public(canvas_id):
    canvas_info = db.execute("SELECT owner_id, is_public FROM canvases WHERE id = ?", canvas_id)
    if not canvas_info or canvas_info[0]["owner_id"] != session["user_id"]: return apology("Permission denied", 403)
    new_status = not canvas_info[0]["is_public"]
    db.execute("UPDATE canvases SET is_public = ? WHERE id = ?", new_status, canvas_id)
    flash(f"Canvas is now {'public' if new_status else 'private'}.")
    return redirect(f"/canvas/{canvas_id}")

@app.route("/admin")
@login_required
@admin_required
def admin_panel():
    all_users = db.execute("SELECT id, username, role FROM users")
    all_canvases = db.execute("SELECT c.id, c.name, u.username as owner_name, c.is_public FROM canvases c LEFT JOIN users u ON c.owner_id = u.id")
    return render_template("admin.html", users=all_users, canvases=all_canvases)

@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == session["user_id"]: return apology("Cannot delete yourself", 400)
    db.execute("DELETE FROM pixel_history WHERE modifier_id = ?", user_id)
    db.execute("DELETE FROM canvases WHERE owner_id = ?", user_id)
    db.execute("DELETE FROM users WHERE id = ?", user_id)
    flash("User and all their data have been deleted.")
    return redirect("/admin")

@app.route("/admin/toggle_public/<int:canvas_id>", methods=["POST"])
@login_required
@admin_required
def admin_toggle_public(canvas_id):
    canvas_info = db.execute("SELECT is_public FROM canvases WHERE id = ?", canvas_id)
    if not canvas_info: return apology("Canvas not found", 404)
    new_status = not canvas_info[0]["is_public"]
    db.execute("UPDATE canvases SET is_public = ? WHERE id = ?", new_status, canvas_id)
    flash("Canvas public status toggled.")
    return redirect("/admin")

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        username, password = request.form.get("username"), request.form.get("password")
        if not username or not password: return apology("must provide username and password", 400)
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password): return apology("invalid username and/or password", 403)
        session["user_id"], session["username"], session["role"] = rows[0]["id"], rows[0]["username"], rows[0]["role"]
        flash("Logged in successfully!")
        return redirect("/")
    else: return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username, password, confirmation = request.form.get("username"), request.form.get("password"), request.form.get("confirmation")
        if not username or not password or not confirmation: return apology("must fill all fields", 400)
        if password != confirmation: return apology("passwords do not match", 400)
        if db.execute("SELECT * FROM users WHERE username = ?", username): return apology("username already exists", 400)
        hash_val = generate_password_hash(password)
        user_id = db.execute("INSERT INTO users (username, hash, role) VALUES (?, ?, ?)", username, hash_val, 'user')
        rows = db.execute("SELECT * FROM users WHERE id = ?", user_id)
        session["user_id"], session["username"], session["role"] = rows[0]["id"], rows[0]["username"], rows[0]["role"]
        flash("Registered successfully!")
        return redirect("/")
    else: return render_template("register.html")

@socketio.on('join_canvas')
def handle_join_canvas(data):
    join_room(data['canvas_id'])

@socketio.on('place_pixel')
def handle_place_pixel(data):
    canvas_id, x, y, color, user_id = data['canvas_id'], data['x'], data['y'], data['color'], session.get('user_id')
    current_canvas = db.execute("SELECT canvas_data, is_community FROM canvases WHERE id = ?", canvas_id)
    if not current_canvas: return
    canvas_data = json.loads(current_canvas[0]['canvas_data'])
    if 0 <= y < len(canvas_data) and 0 <= x < len(canvas_data[y]): canvas_data[y][x] = color
    db.execute("UPDATE canvases SET canvas_data = ? WHERE id = ?", json.dumps(canvas_data), canvas_id)
    if current_canvas[0]['is_community']: db.execute("INSERT INTO pixel_history (canvas_id, x, y, modifier_id, color) VALUES (?, ?, ?, ?, ?)", canvas_id, x, y, user_id, color)
    emit('pixel_placed', data, room=canvas_id, include_self=False)

@socketio.on('request_history')
def handle_request_history(data):
    canvas_id, x, y = data['canvas_id'], data['x'], data['y']
    history_data = db.execute("SELECT u.username, p.timestamp FROM pixel_history p JOIN users u ON p.modifier_id = u.id WHERE p.canvas_id = ? AND p.x = ? AND p.y = ? ORDER BY p.timestamp DESC LIMIT 1", canvas_id, x, y)
    if history_data: emit('history_response', history_data[0])
    else: emit('history_response', {'username': 'N/A', 'timestamp': 'Never modified'})

if __name__ == '__main__':
    initialize_database()
    socketio.run(app, debug=True)