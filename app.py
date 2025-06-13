import os
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from cs50 import SQL
from functools import wraps

# --- App Configuration ---
app = Flask(__name__)

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///project.db")

# --- Helper Functions ---
def login_required(f):
    """
    Decorate routes to require login.
    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def apology(message, code=400):
    """Render message as an apology to user."""
    return render_template("apology.html", top=code, bottom=message), code


# --- Main Routes ---
@app.route("/")
def index():
    """Redirect to canvas or login page"""
    if session.get("user_id"):
        return redirect("/canvas")
    return redirect("/login")


@app.route("/canvas")
@login_required
def canvas():
    """Show the drawing canvas"""
    return render_template("canvas.html")


# --- Authentication Routes ---
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    session.clear() # Forget any user_id

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username:
            return apology("must provide username", 400)
        elif not password:
            return apology("must provide password", 400)

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return apology("invalid username and/or password", 403)

        session["user_id"] = rows[0]["id"]
        session["username"] = rows[0]["username"]

        flash("Logged in successfully!")
        return redirect("/canvas")

    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""
    session.clear()
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            return apology("must provide username", 400)
        elif not password:
            return apology("must provide password", 400)
        elif password != confirmation:
            return apology("passwords do not match", 400)

        # Check if username already exists
        if len(db.execute("SELECT * FROM users WHERE username = ?", username)) > 0:
            return apology("username already exists", 400)

        # Insert new user into database
        hash = generate_password_hash(password)
        db.execute("INSERT INTO users (username, hash, role) VALUES (?, ?, ?)", username, hash, 'user')

        # Log the new user in automatically
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        session["user_id"] = rows[0]["id"]
        session["username"] = rows[0]["username"]
        
        flash("Registered successfully!")
        return redirect("/canvas")

    else:
        return render_template("register.html")

# --- Database Initialization ---
def setup_database():
    """Create database tables if they don't exist"""
    print("Setting up database...")
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        );
    """)
    print("Database setup complete.")

if __name__ == '__main__':
    # Check if database exists, if not, create it
    if not os.path.exists("project.db"):
        setup_database()
    app.run(debug=True)