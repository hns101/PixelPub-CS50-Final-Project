import os
import sqlite3
import json
from flask import Flask, flash, redirect, render_template, request, session, Response
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_socketio import SocketIO, emit, join_room
from cs50 import SQL
from functools import wraps
from PIL import Image, ImageDraw
import io

# --- Database Initialization ---
DB_FILE = "project.db"

def initialize_database():
    """Creates and initializes all database tables if they don't exist."""
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    print("Database file checked. Creating/updating tables...")

    cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user', avatar_data TEXT);")
    try:
        cur.execute("ALTER TABLE users ADD COLUMN avatar_data TEXT;")
    except:
        pass # Column likely exists

    cur.execute("CREATE TABLE IF NOT EXISTS canvases (id INTEGER PRIMARY KEY, name TEXT NOT NULL, width INTEGER, height INTEGER, owner_id INTEGER, is_public BOOLEAN DEFAULT 0, is_community BOOLEAN DEFAULT 0, canvas_data TEXT, FOREIGN KEY(owner_id) REFERENCES users(id));")
    cur.execute("CREATE TABLE IF NOT EXISTS friendships (id INTEGER PRIMARY KEY, user_one_id INTEGER, user_two_id INTEGER, status TEXT, action_user_id INTEGER, FOREIGN KEY(user_one_id) REFERENCES users(id), FOREIGN KEY(user_two_id) REFERENCES users(id), UNIQUE(user_one_id, user_two_id));")
    cur.execute("CREATE TABLE IF NOT EXISTS pixel_history (id INTEGER PRIMARY KEY, canvas_id INTEGER, x INTEGER, y INTEGER, modifier_id INTEGER, color TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(canvas_id) REFERENCES canvases(id), FOREIGN KEY(modifier_id) REFERENCES users(id));")
    cur.execute("CREATE TABLE IF NOT EXISTS pubs (id INTEGER PRIMARY KEY, name TEXT NOT NULL, owner_id INTEGER, is_private BOOLEAN NOT NULL, canvas_id INTEGER NOT NULL, FOREIGN KEY(owner_id) REFERENCES users(id), FOREIGN KEY(canvas_id) REFERENCES canvases(id));")
    cur.execute("CREATE TABLE IF NOT EXISTS pub_members (id INTEGER PRIMARY KEY, pub_id INTEGER NOT NULL, user_id INTEGER NOT NULL, FOREIGN KEY(pub_id) REFERENCES pubs(id), FOREIGN KEY(user_id) REFERENCES users(id), UNIQUE(pub_id, user_id));")
    cur.execute("CREATE TABLE IF NOT EXISTS chat_messages (id INTEGER PRIMARY KEY, pub_id INTEGER NOT NULL, user_id INTEGER NOT NULL, content TEXT NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(pub_id) REFERENCES pubs(id), FOREIGN KEY(user_id) REFERENCES users(id));")

    community_pubs_data = [("The Garden", 48, 48), ("The City", 64, 32), ("The Ocean", 32, 64)]
    for name, width, height in community_pubs_data:
        pub_exists = cur.execute("SELECT id FROM pubs WHERE name = ? AND owner_id IS NULL", (name,)).fetchone()
        if pub_exists is None:
            print(f"Creating community pub: {name}")
            canvas_name = f"Community: {name}"
            initial_data = json.dumps([['#FFFFFF' for _ in range(width)] for _ in range(height)])
            cur.execute("INSERT INTO canvases (name, width, height, is_community, canvas_data) VALUES (?, ?, ?, ?, ?)", (canvas_name, width, height, 1, initial_data))
            canvas_id = cur.lastrowid
            cur.execute("INSERT INTO pubs (name, owner_id, is_private, canvas_id) VALUES (?, NULL, ?, ?)", (name, False, canvas_id))
    con.commit()
    con.close()
    print("Database setup complete.")

initialize_database()
db = SQL(f"sqlite:///{DB_FILE}")

# App Config & Helpers
app = Flask(__name__)
app.config["SECRET_KEY"] = "a_super_secret_key_for_socketio_final"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
socketio = SocketIO(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None: return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def apology(message, code=400):
    return render_template("apology.html", top=code, bottom=message), code

# --- Routes ---
@app.route("/")
def index():
    if session.get("user_id"): return redirect("/dashboard")
    return redirect("/login")

@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    my_pubs = db.execute("SELECT p.* FROM pubs p JOIN pub_members pm ON p.id = pm.pub_id WHERE pm.user_id = ? AND p.owner_id IS NOT NULL", user_id)
    community_pubs = db.execute("SELECT * FROM pubs WHERE owner_id IS NULL")
    return render_template("dashboard.html", my_pubs=my_pubs, community_pubs=community_pubs)

@app.route("/create_pub", methods=["GET", "POST"])
@login_required
def create_pub():
    if request.method == "POST":
        user_id = session["user_id"]
        name = request.form.get("name")
        is_private = request.form.get("is_private") == "true"
        try:
            width = int(request.form.get("width"))
            height = int(request.form.get("height"))
        except (ValueError, TypeError):
            return apology("Width and height must be valid numbers.", 400)
        if not name or len(name) > 50: return apology("Invalid pub name", 400)
        if not (16 <= width <= 128 and 16 <= height <= 128): return apology("Width and height must be between 16 and 128.", 400)
        canvas_name = f"{name}'s Canvas"
        initial_data = json.dumps([['#FFFFFF' for _ in range(width)] for _ in range(height)])
        canvas_id = db.execute("INSERT INTO canvases (name, width, height, owner_id, canvas_data) VALUES (?, ?, ?, ?, ?)", canvas_name, width, height, user_id, initial_data)
        pub_id = db.execute("INSERT INTO pubs (name, owner_id, is_private, canvas_id) VALUES (?, ?, ?, ?)", name, user_id, is_private, canvas_id)
        db.execute("INSERT INTO pub_members (pub_id, user_id) VALUES (?, ?)", pub_id, user_id)
        flash("Pub created successfully!")
        return redirect(f"/pub/{pub_id}")
    else:
        return render_template("create_pub.html")

@app.route("/pub/<int:pub_id>")
@login_required
def pub(pub_id):
    user_id = session["user_id"]
    pub_info = db.execute("SELECT * FROM pubs WHERE id = ?", pub_id)
    if not pub_info: return apology("Pub not found", 404)
    pub_info = pub_info[0]
    member_check = db.execute("SELECT * FROM pub_members WHERE pub_id = ? AND user_id = ?", pub_id, user_id)
    if not member_check and pub_info["is_private"]: return apology("This pub is private", 403)
    if not member_check and not pub_info["is_private"]:
        db.execute("INSERT OR IGNORE INTO pub_members (pub_id, user_id) VALUES (?, ?)", pub_id, user_id)
    canvas_info = db.execute("SELECT * FROM canvases WHERE id = ?", pub_info["canvas_id"])[0]
    chat_history = db.execute("SELECT m.*, u.username, u.id as avatar_id FROM chat_messages m JOIN users u ON m.user_id = u.id WHERE m.pub_id = ? ORDER BY m.timestamp ASC LIMIT 100", pub_id)
    friends_to_invite = db.execute("SELECT u.id, u.username FROM users u JOIN friendships f ON (u.id = f.user_one_id OR u.id = f.user_two_id) WHERE (f.user_one_id = ? OR f.user_two_id = ?) AND f.status = 'accepted' AND u.id != ? AND u.id NOT IN (SELECT user_id FROM pub_members WHERE pub_id = ?)", user_id, user_id, user_id, pub_id)
    return render_template("pub.html", pub=pub_info, canvas=canvas_info, chat=chat_history, friends=friends_to_invite)

@app.route("/invite_to_pub/<int:pub_id>", methods=["POST"])
@login_required
def invite_to_pub(pub_id):
    owner_id_result = db.execute("SELECT owner_id FROM pubs WHERE id = ?", pub_id)
    if not owner_id_result or owner_id_result[0]["owner_id"] != session["user_id"]: return apology("Only the pub owner can invite friends", 403)
    friend_id = request.form.get("friend_id")
    if not friend_id: return apology("No friend selected", 400)
    try:
        db.execute("INSERT INTO pub_members (pub_id, user_id) VALUES (?, ?)", pub_id, friend_id)
        flash("Friend invited to the pub!")
    except:
        flash("This user is already a member.")
    return redirect(f"/pub/{pub_id}")

@app.route("/canvas_preview/<int:canvas_id>.png")
def canvas_preview(canvas_id):
    canvas_data = db.execute("SELECT width, height, canvas_data FROM canvases WHERE id = ?", canvas_id)
    if not canvas_data: return apology("Canvas not found", 404)
    c = canvas_data[0]
    width, height, pixels_json = c["width"], c["height"], c["canvas_data"]
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    try:
        pixels = json.loads(pixels_json)
        for y, row in enumerate(pixels):
            for x, color in enumerate(row):
                if color and color != '#FFFFFF': draw.point((x, y), fill=color)
    except (json.JSONDecodeError, TypeError): pass
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return Response(img_io.getvalue(), mimetype='image/png')

@app.route("/avatar/<int:user_id>.png")
def avatar(user_id):
    user = db.execute("SELECT avatar_data FROM users WHERE id = ?", user_id)
    pixel_data_json = user[0]['avatar_data'] if user and user[0]['avatar_data'] else None
    AVATAR_SIZE, PIXEL_SIZE = 32, 10
    img_size = AVATAR_SIZE * PIXEL_SIZE
    img = Image.new('RGB', (img_size, img_size), color='#eeeeee')
    draw = ImageDraw.Draw(img)
    if pixel_data_json:
        try:
            pixel_data = json.loads(pixel_data_json)
            for y, row in enumerate(pixel_data):
                for x, color in enumerate(row):
                    if color: draw.rectangle([x*PIXEL_SIZE, y*PIXEL_SIZE, (x+1)*PIXEL_SIZE-1, (y+1)*PIXEL_SIZE-1], fill=color)
        except (json.JSONDecodeError, TypeError): pass
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return Response(img_io.getvalue(), mimetype='image/png')

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    user_id = session["user_id"]
    if request.method == "POST":
        avatar_data = request.form.get("avatar_data")
        if not avatar_data: return apology("No avatar data received", 400)
        try: json.loads(avatar_data)
        except json.JSONDecodeError: return apology("Invalid avatar data format", 400)
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
    friends_list = db.execute("SELECT u.id, u.username FROM users u JOIN friendships f ON (u.id=f.user_one_id OR u.id=f.user_two_id) WHERE (f.user_one_id=? OR f.user_two_id=?) AND f.status='accepted' AND u.id!=?", user_id, user_id, user_id)
    pending_received = db.execute("SELECT f.id, u.username, u.id as user_id FROM friendships f JOIN users u ON f.user_one_id=u.id WHERE f.user_two_id=? AND f.status='pending'", user_id)
    other_users = db.execute("SELECT id, username FROM users WHERE id != ? AND id NOT IN (SELECT user_one_id FROM friendships WHERE user_two_id = ?) AND id NOT IN (SELECT user_two_id FROM friendships WHERE user_one_id = ?)", user_id, user_id, user_id)
    return render_template("friends.html", friends=friends_list, pending_received=pending_received, other_users=other_users)

@app.route("/send_request/<int:recipient_id>", methods=["POST"])
@login_required
def send_request(recipient_id):
    sender_id = session["user_id"]
    if sender_id == recipient_id: return apology("You cannot send a friend request to yourself.", 400)
    user_one, user_two = min(sender_id, recipient_id), max(sender_id, recipient_id)
    if db.execute("SELECT * FROM friendships WHERE user_one_id = ? AND user_two_id = ?", user_one, user_two):
        flash("A friend request is already pending or you are already friends.")
        return redirect("/friends")
    db.execute("INSERT INTO friendships (user_one_id, user_two_id, status, action_user_id) VALUES (?, ?, 'pending', ?)", user_one, user_two, sender_id)
    flash("Friend request sent!")
    return redirect("/friends")

@app.route("/accept_request/<int:friendship_id>", methods=["POST"])
@login_required
def accept_request(friendship_id):
    friendship = db.execute("SELECT * FROM friendships WHERE id = ?", friendship_id)
    if not friendship or friendship[0]['user_two_id'] != session['user_id']: return apology("Invalid request", 403)
    db.execute("UPDATE friendships SET status = 'accepted' WHERE id = ?", friendship_id)
    flash("Friend request accepted!")
    return redirect("/friends")

@app.route("/decline_request/<int:friendship_id>", methods=["POST"])
@login_required
def decline_request(friendship_id):
    db.execute("DELETE FROM friendships WHERE id = ? AND (user_one_id = ? OR user_two_id = ?)", friendship_id, session['user_id'], session['user_id'])
    flash("Friend request handled.")
    return redirect("/friends")

# --- Authentication Routes ---
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
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username, password, confirmation = request.form.get("username"), request.form.get("password"), request.form.get("confirmation")
        if not username or not password or not confirmation: return apology("must fill all fields", 400)
        if password != confirmation: return apology("passwords do not match", 400)
        if db.execute("SELECT * FROM users WHERE username = ?", username): return apology("username already exists", 400)
        hash_val = generate_password_hash(password)
        default_avatar = json.dumps([['#FFFFFF' for _ in range(32)] for _ in range(32)])
        user_id = db.execute("INSERT INTO users (username, hash, role, avatar_data) VALUES (?, ?, ?, ?)", username, hash_val, 'user', default_avatar)
        rows = db.execute("SELECT * FROM users WHERE id = ?", user_id)
        session["user_id"], session["username"], session["role"] = rows[0]["id"], rows[0]["username"], rows[0]["role"]
        flash("Registered successfully!")
        return redirect("/")
    return render_template("register.html")

# --- SocketIO Handlers ---
@socketio.on('join_pub')
def handle_join_pub(data):
    if 'user_id' not in session: return
    join_room(f"pub_{data['pub_id']}")

@socketio.on('place_pixel')
def handle_place_pixel(data):
    if 'user_id' not in session: return
    pub_id = data.get('pub_id')
    emit('pixel_placed', data, room=f"pub_{pub_id}", include_self=False)

@socketio.on('save_canvas_state')
def handle_save_canvas_state(data):
    user_id = session.get('user_id')
    if not user_id: return
    canvas_id, canvas_data = data.get('canvas_id'), data.get('canvas_data')
    if not canvas_id or not canvas_data: return
    db.execute("UPDATE canvases SET canvas_data = ? WHERE id = ?", json.dumps(canvas_data), canvas_id)
    print(f"Canvas {canvas_id} saved by user {user_id}")
    
@socketio.on('log_pixel_history')
def handle_log_pixel_history(data):
    user_id = session.get('user_id')
    if not user_id: return
    canvas_id, pixels = data.get('canvas_id'), data.get('pixels')
    if not canvas_id or not pixels: return
    for pixel in pixels:
        db.execute("INSERT INTO pixel_history (canvas_id, x, y, modifier_id, color) VALUES (?, ?, ?, ?, ?)", canvas_id, pixel['x'], pixel['y'], user_id, pixel['color'])
    print(f"Logged {len(pixels)} pixels to history for canvas {canvas_id} by user {user_id}")

@socketio.on('request_history')
def handle_request_history(data):
    canvas_id, x, y = data['canvas_id'], data['x'], data['y']
    history_data = db.execute("SELECT u.username, p.timestamp FROM pixel_history p JOIN users u ON p.modifier_id = u.id WHERE p.canvas_id = ? AND p.x = ? AND p.y = ? ORDER BY p.timestamp DESC LIMIT 1", canvas_id, x, y)
    if history_data:
        emit('history_response', history_data[0])
    else:
        emit('history_response', {'username': 'N/A', 'timestamp': 'Never modified'})

@socketio.on('send_message')
def handle_send_message(data):
    user_id = session.get('user_id')
    if not user_id: return
    pub_id, content = data['pub_id'], data['content'].strip()
    if not (1 <= len(content) <= 250): return
    db.execute("INSERT INTO chat_messages (pub_id, user_id, content) VALUES (?, ?, ?)", pub_id, user_id, content)
    db.execute("DELETE FROM chat_messages WHERE id IN (SELECT id FROM chat_messages WHERE pub_id = ? ORDER BY timestamp DESC LIMIT -1 OFFSET 100)", pub_id)
    message_data = {'username': session['username'], 'avatar_id': user_id, 'content': content}
    emit('new_message', message_data, room=f"pub_{pub_id}")

if __name__ == '__main__':
    socketio.run(app, debug=True)