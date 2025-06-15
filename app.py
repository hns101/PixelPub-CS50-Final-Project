import os
import sqlite3
import json
from flask import Flask, flash, redirect, render_template, request, session, Response
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_socketio import SocketIO, emit, join_room, leave_room
from cs50 import SQL
from functools import wraps
from PIL import Image, ImageDraw # Pillow library for image generation
import io

# --- Database Initialization ---
DB_FILE = "project.db"

def initialize_database():
    """Creates and initializes the database and tables if they don't exist."""
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    print("Database file checked. Creating/updating tables...")
    
    # Updated users table with avatar_data
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            avatar_data TEXT
        );
    """)
    
    # Add avatar_data column if it doesn't exist (for existing databases)
    try:
        cur.execute("ALTER TABLE users ADD COLUMN avatar_data TEXT;")
    except sqlite3.OperationalError:
        print("avatar_data column already exists.")

    # New friendships table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS friendships (
            id INTEGER PRIMARY KEY,
            user_one_id INTEGER NOT NULL,
            user_two_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            action_user_id INTEGER NOT NULL,
            FOREIGN KEY(user_one_id) REFERENCES users(id),
            FOREIGN KEY(user_two_id) REFERENCES users(id),
            FOREIGN KEY(action_user_id) REFERENCES users(id),
            UNIQUE(user_one_id, user_two_id)
        );
    """)

    # --- Other tables (canvases, pixel_history) are unchanged ---
    cur.execute("CREATE TABLE IF NOT EXISTS canvases (id INTEGER PRIMARY KEY, name TEXT NOT NULL, width INTEGER, height INTEGER, owner_id INTEGER, is_public BOOLEAN DEFAULT 0, is_community BOOLEAN DEFAULT 0, canvas_data TEXT, FOREIGN KEY(owner_id) REFERENCES users(id));")
    cur.execute("CREATE TABLE IF NOT EXISTS pixel_history (id INTEGER PRIMARY KEY, canvas_id INTEGER NOT NULL, x INTEGER NOT NULL, y INTEGER NOT NULL, modifier_id INTEGER NOT NULL, color TEXT NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(canvas_id) REFERENCES canvases(id), FOREIGN KEY(modifier_id) REFERENCES users(id));")
    
    # ... rest of initialization ...
    community_canvases = [("The Garden", 48, 48), ("The City", 64, 32), ("The Ocean", 32, 64)]
    for name, width, height in community_canvases:
        cur.execute("SELECT id FROM canvases WHERE is_community = 1 AND name = ?", (name,))
        if cur.fetchone() is None:
            initial_data = [['#FFFFFF' for _ in range(width)] for _ in range(height)]
            cur.execute("INSERT INTO canvases (name, width, height, is_community, canvas_data) VALUES (?, ?, ?, ?, ?)", (name, width, height, 1, json.dumps(initial_data)))

    con.commit()
    con.close()
    print("Database setup complete.")

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

# Helper functions (login_required, admin_required, apology) are unchanged
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

# --- Main Routes ---
# ... / and /gallery and /community routes are unchanged ...
@app.route("/")
def index():
    if session.get("user_id"): return redirect("/dashboard")
    return redirect("/login")

@app.route("/gallery")
def gallery():
    public_canvases = db.execute("SELECT c.*, u.username FROM canvases c JOIN users u ON c.owner_id = u.id WHERE c.is_public = 1")
    return render_template("gallery.html", canvases=public_canvases)

@app.route("/community")
def community():
    community_canvases = db.execute("SELECT * FROM canvases WHERE is_community = 1")
    return render_template("community.html", canvases=community_canvases)

# --- NEW: Avatar & Social Routes ---
@app.route("/avatar/<int:user_id>.png")
def avatar(user_id):
    """Generates a PNG image from a user's avatar data."""
    user = db.execute("SELECT avatar_data FROM users WHERE id = ?", user_id)
    pixel_data_json = user[0]['avatar_data'] if user and user[0]['avatar_data'] else None
    
    AVATAR_SIZE = 32
    PIXEL_SIZE = 10 # Each "pixel" in the data will be 10x10 in the final image
    img_size = AVATAR_SIZE * PIXEL_SIZE
    
    img = Image.new('RGB', (img_size, img_size), color='white')
    draw = ImageDraw.Draw(img)

    if pixel_data_json:
        pixel_data = json.loads(pixel_data_json)
        for y, row in enumerate(pixel_data):
            for x, color in enumerate(row):
                if color: # Only draw if color is not null/empty
                    draw.rectangle(
                        [x*PIXEL_SIZE, y*PIXEL_SIZE, (x+1)*PIXEL_SIZE-1, (y+1)*PIXEL_SIZE-1],
                        fill=color
                    )

    # Serve the image directly
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return Response(img_io.getvalue(), mimetype='image/png')

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    user_id = session["user_id"]
    if request.method == "POST":
        # This will handle the avatar update
        avatar_data = request.form.get("avatar_data")
        if not avatar_data:
            return apology("No avatar data received", 400)
        
        # Basic validation (is it valid JSON?)
        try:
            json.loads(avatar_data)
        except json.JSONDecodeError:
            return apology("Invalid avatar data format", 400)
        
        db.execute("UPDATE users SET avatar_data = ? WHERE id = ?", avatar_data, user_id)
        flash("Avatar updated successfully!")
        return redirect("/settings")
    else:
        user = db.execute("SELECT avatar_data FROM users WHERE id = ?", user_id)
        current_avatar_data = user[0]['avatar_data'] or 'null'
        return render_template("settings.html", current_avatar_data=current_avatar_data)

@app.route("/friends")
@login_required
def friends():
    user_id = session["user_id"]
    
    # Friends (status is 'accepted')
    friends = db.execute("""
        SELECT u.id, u.username FROM users u JOIN friendships f ON (u.id = f.user_one_id OR u.id = f.user_two_id)
        WHERE (f.user_one_id = ? OR f.user_two_id = ?) AND f.status = 'accepted' AND u.id != ?
    """, user_id, user_id, user_id)
    
    # Pending requests sent TO me
    pending_received = db.execute("""
        SELECT f.id, u.username, u.id as user_id FROM friendships f JOIN users u ON f.user_one_id = u.id
        WHERE f.user_two_id = ? AND f.status = 'pending'
    """, user_id)

    return render_template("friends.html", friends=friends, pending_received=pending_received)

@app.route("/users")
@login_required
def users():
    """Page to browse all users"""
    all_users = db.execute("SELECT id, username FROM users WHERE id != ?", session['user_id'])
    return render_template("users.html", users=all_users)

@app.route("/send_request/<int:recipient_id>", methods=["POST"])
@login_required
def send_request(recipient_id):
    sender_id = session["user_id"]
    
    # Can't befriend yourself
    if sender_id == recipient_id:
        return apology("You cannot send a friend request to yourself.", 400)

    # Ensure users are ordered to prevent duplicate entries (e.g., 1-2 and 2-1)
    user_one = min(sender_id, recipient_id)
    user_two = max(sender_id, recipient_id)

    # Check if a friendship already exists
    existing = db.execute("SELECT * FROM friendships WHERE user_one_id = ? AND user_two_id = ?", user_one, user_two)
    if existing:
        flash("A friend request is already pending or you are already friends.")
        return redirect("/users")

    db.execute(
        "INSERT INTO friendships (user_one_id, user_two_id, status, action_user_id) VALUES (?, ?, 'pending', ?)",
        user_one, user_two, sender_id
    )
    flash("Friend request sent!")
    return redirect("/users")

@app.route("/accept_request/<int:friendship_id>", methods=["POST"])
@login_required
def accept_request(friendship_id):
    db.execute("UPDATE friendships SET status = 'accepted' WHERE id = ? AND user_two_id = ?", friendship_id, session["user_id"])
    flash("Friend request accepted!")
    return redirect("/friends")

@app.route("/decline_request/<int:friendship_id>", methods=["POST"])
@login_required
def decline_request(friendship_id):
    # This also handles cancelling a sent request
    db.execute("DELETE FROM friendships WHERE id = ?", friendship_id)
    flash("Friend request declined.")
    return redirect("/friends")

# ... other routes and SocketIO handlers from previous phase remain ...
# (Dashboard, canvas, auth, etc.)
@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    user_id = session["user_id"]
    if request.method == "POST":
        name, width, height = request.form.get("name"), int(request.form.get("width")), int(request.form.get("height"))
        if not name or not (16 <= width <= 64 and 16 <= height <= 64): return apology("Invalid canvas details", 400)
        initial_data = [['#FFFFFF' for _ in range(width)] for _ in range(height)]
        db.execute("INSERT INTO canvases (name, width, height, owner_id, canvas_data) VALUES (?, ?, ?, ?, ?)", name, width, height, user_id, json.dumps(initial_data))
        flash("Canvas created successfully!")
        return redirect("/dashboard")
    else:
        my_canvases = db.execute("SELECT * FROM canvases WHERE owner_id = ?", user_id)
        return render_template("dashboard.html", canvases=my_canvases)

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

# ... login, logout, register, etc. ...
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
        # Set default avatar on registration
        default_avatar = json.dumps([[None for _ in range(32)] for _ in range(32)])
        user_id = db.execute("INSERT INTO users (username, hash, role, avatar_data) VALUES (?, ?, ?, ?)", username, hash_val, 'user', default_avatar)
        rows = db.execute("SELECT * FROM users WHERE id = ?", user_id)
        session["user_id"], session["username"], session["role"] = rows[0]["id"], rows[0]["username"], rows[0]["role"]
        flash("Registered successfully!")
        return redirect("/")
    else: return render_template("register.html")

# --- SocketIO Handlers ---
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
