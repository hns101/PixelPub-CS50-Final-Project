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
    """Creates and initializes the database and tables if they don't exist."""
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    print("Database file checked. Creating tables if not exist...")
    
    # Create the 'users' table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        );
    """)
    
    # Create the 'canvases' table for Milestone 2
    cur.execute("""
        CREATE TABLE IF NOT EXISTS canvases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            width INTEGER NOT NULL,
            height INTEGER NOT NULL,
            owner_id INTEGER,
            is_public BOOLEAN DEFAULT 0,
            is_community BOOLEAN DEFAULT 0,
            canvas_data TEXT,
            FOREIGN KEY(owner_id) REFERENCES users(id)
        );
    """)

    # Check if the community canvas exists, if not, create it
    cur.execute("SELECT id FROM canvases WHERE is_community = 1")
    if cur.fetchone() is None:
        print("Creating default community canvas...")
        # Create an empty canvas state (a 2D array of white pixels)
        width, height = 32, 32
        initial_data = [['#FFFFFF' for _ in range(width)] for _ in range(height)]
        cur.execute(
            "INSERT INTO canvases (name, width, height, is_community, canvas_data) VALUES (?, ?, ?, ?, ?)",
            ("Community Canvas", width, height, 1, json.dumps(initial_data))
        )

    con.commit()
    con.close()
    print("Database setup complete.")

# Run initialization check BEFORE setting up the cs50.SQL object
if not os.path.exists(DB_FILE):
    initialize_database()

# Now that we're sure project.db exists, we can connect with the CS50 library
db = SQL(f"sqlite:///{DB_FILE}")

# --- App Configuration ---
app = Flask(__name__)
app.config["SECRET_KEY"] = "a_super_secret_key_for_socketio" # Change this in a real app
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
socketio = SocketIO(app)


# --- Helper Functions ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def apology(message, code=400):
    return render_template("apology.html", top=code, bottom=message), code


# --- Main Routes ---
@app.route("/")
def index():
    if session.get("user_id"):
        # For now, redirect all users to the community canvas (ID 1)
        return redirect("/canvas/1")
    return redirect("/login")


@app.route("/canvas/<int:canvas_id>")
@login_required
def canvas(canvas_id):
    """Show the drawing canvas for a specific ID"""
    canvas_info = db.execute("SELECT * FROM canvases WHERE id = ?", canvas_id)
    if not canvas_info:
        return apology("Canvas not found", 404)
    return render_template("canvas.html", canvas_info=canvas_info[0])


# --- Authentication Routes (No changes needed) ---
@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return apology("must provide username and password", 400)

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return apology("invalid username and/or password", 403)

        session["user_id"] = rows[0]["id"]
        session["username"] = rows[0]["username"]
        flash("Logged in successfully!")
        return redirect("/")
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username or not password or not confirmation:
            return apology("must fill all fields", 400)
        if password != confirmation:
            return apology("passwords do not match", 400)

        if db.execute("SELECT * FROM users WHERE username = ?", username):
            return apology("username already exists", 400)

        hash_val = generate_password_hash(password)
        db.execute("INSERT INTO users (username, hash, role) VALUES (?, ?, ?)", username, hash_val, 'user')

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        session["user_id"] = rows[0]["id"]
        session["username"] = rows[0]["username"]
        flash("Registered successfully!")
        return redirect("/")
    else:
        return render_template("register.html")


# --- SocketIO Event Handlers ---
@socketio.on('join_canvas')
def handle_join_canvas(data):
    """Client joins a room for a specific canvas"""
    canvas_id = data['canvas_id']
    username = session.get("username", "Anonymous")
    # A "room" is a channel that isolates communication. We name the room after the canvas ID.
    join_room(canvas_id) 
    print(f"{username} has joined canvas {canvas_id}")


@socketio.on('place_pixel')
def handle_place_pixel(data):
    """Receives a pixel, updates the DB, and broadcasts it."""
    canvas_id = data['canvas_id']
    x = data['x']
    y = data['y']
    color = data['color']
    username = session.get('username')

    # 1. Get current canvas data from DB
    current_canvas = db.execute("SELECT canvas_data, width, height FROM canvases WHERE id = ?", canvas_id)
    if not current_canvas:
        return # Canvas doesn't exist

    canvas_data = json.loads(current_canvas[0]['canvas_data'])
    
    # 2. Update the specific pixel in the data
    if 0 <= y < len(canvas_data) and 0 <= x < len(canvas_data[y]):
        canvas_data[y][x] = color
    
    # 3. Save the updated data back to the DB
    db.execute("UPDATE canvases SET canvas_data = ? WHERE id = ?", json.dumps(canvas_data), canvas_id)

    # 4. Broadcast the change to everyone in the same room (except the sender)
    emit('pixel_placed', data, room=canvas_id, include_self=False)
    print(f"Pixel placed on canvas {canvas_id} at ({x},{y}) by {username}")


if __name__ == '__main__':
    initialize_database()
    # Use socketio.run() instead of app.run()
    socketio.run(app, debug=True)
