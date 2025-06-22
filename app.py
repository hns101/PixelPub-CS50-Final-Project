import os
import json
import random
from flask import Flask, flash, redirect, render_template, request, session, Response
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_socketio import SocketIO, emit, join_room
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, and_
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from functools import wraps
from PIL import Image, ImageDraw
import io
from datetime import datetime

# --- App & Extension Configuration ---
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "a_very_secret_dev_key_for_local_runs")
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///project.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Add ProxyFix Middleware for deployment
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

Session(app)
db = SQLAlchemy(app)
# CORRECTED: Restored async_mode='gevent' for deployment
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

# --- Database Models (SQLAlchemy ORM) ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    avatar_data = db.Column(db.Text)

class Pub(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_private = db.Column(db.Boolean, nullable=False, default=False)
    canvas_id = db.Column(db.Integer, db.ForeignKey('canvas.id'), unique=True, nullable=False)
    canvas = db.relationship('Canvas', backref='pub', uselist=False, cascade="all, delete")
    members = db.relationship('PubMember', backref='pub', cascade="all, delete", lazy='dynamic')
    owner = db.relationship('User', backref='pubs')

class Canvas(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    canvas_data = db.Column(db.Text)
    history = db.relationship('PixelHistory', backref='canvas', cascade="all, delete", lazy='dynamic')

class PubMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pub_id = db.Column(db.Integer, db.ForeignKey('pub.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('pub_id', 'user_id'),)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pub_id = db.Column(db.Integer, db.ForeignKey('pub.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User')

class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_one_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_two_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    action_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('user_one_id', 'user_two_id'),)

class PixelHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    canvas_id = db.Column(db.Integer, db.ForeignKey('canvas.id'), nullable=False)
    x = db.Column(db.Integer, nullable=False)
    y = db.Column(db.Integer, nullable=False)
    modifier_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    color = db.Column(db.String(7), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User')

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
        if session.get("role") != "admin":
            return apology("Admin access required", 403)
        return f(*args, **kwargs)
    return decorated_function

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code

# --- All HTTP Routes ---
@app.route("/")
def index():
    if session.get("user_id") or session.get("guest_name"): return redirect("/dashboard")
    return redirect("/login")

@app.route("/dashboard")
def dashboard():
    user_id = session.get("user_id")
    my_pubs = []
    if user_id:
        my_pubs = Pub.query.join(PubMember).filter(PubMember.user_id == user_id, Pub.owner_id != None).all()
    
    lobby_pub = Pub.query.filter_by(name='The Guest Pub').first()
    community_pubs = Pub.query.filter(Pub.owner_id == None, Pub.name != 'The Guest Pub').all()
    
    return render_template("dashboard.html", my_pubs=my_pubs, lobby_pub=lobby_pub, community_pubs=community_pubs)

@app.route("/create_pub", methods=["GET", "POST"])
@login_required
def create_pub():
    if request.method == "POST":
        user_id = session["user_id"]
        name, is_private = request.form.get("name"), request.form.get("is_private") == "true"
        try: width, height = int(request.form.get("width")), int(request.form.get("height"))
        except: return apology("Width and height must be valid numbers.", 400)
        if not name or len(name) > 50: return apology("Invalid pub name", 400)
        if not (16 <= width <= 256 and 16 <= height <= 256): return apology("Width/height must be between 16 and 256.", 400)
        
        new_canvas = Canvas(name=f"{name}'s Canvas", width=width, height=height, canvas_data=json.dumps([['#FFFFFF' for _ in range(width)] for _ in range(height)]))
        new_pub = Pub(name=name, owner_id=user_id, is_private=is_private, canvas=new_canvas)
        db.session.add(new_pub)
        db.session.commit()
        
        new_member = PubMember(pub_id=new_pub.id, user_id=user_id)
        db.session.add(new_member)
        db.session.commit()

        flash("Pub created successfully!")
        return redirect(f"/pub/{new_pub.id}")
    else:
        return render_template("create_pub.html")

@app.route("/pub/<int:pub_id>")
def pub(pub_id):
    user_id, guest_name = session.get("user_id"), session.get("guest_name")
    if not user_id and not guest_name: return redirect("/login")
    
    pub_info = Pub.query.get_or_404(pub_id)

    if guest_name and pub_info.name != "The Guest Pub": return apology("Guests can only access The Guest Pub.", 403)
        
    if user_id:
        member_check = PubMember.query.filter_by(pub_id=pub_id, user_id=user_id).first()
        if not member_check and pub_info.is_private: return apology("This pub is private.", 403)
        if not member_check and not pub_info.is_private:
            try:
                db.session.add(PubMember(pub_id=pub_id, user_id=user_id))
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
    
    chat_history_query = ChatMessage.query.options(joinedload(ChatMessage.user)).filter_by(pub_id=pub_id).order_by(ChatMessage.timestamp.asc()).limit(100).all()
    chat_display_data = []
    for message in chat_history_query:
        chat_display_data.append({
            'user_id': message.user_id,
            'username': message.user.username if message.user else 'Guest',
            'timestamp': message.timestamp.strftime('%H:%M'),
            'content': message.content
        })

    friends_to_invite = []
    if user_id:
        friends_subquery = db.session.query(User.id).join(Friendship, or_(User.id == Friendship.user_one_id, User.id == Friendship.user_two_id)).filter(or_(Friendship.user_one_id == user_id, Friendship.user_two_id == user_id), Friendship.status == 'accepted', User.id != user_id)
        members_subquery = db.session.query(PubMember.user_id).filter(PubMember.pub_id == pub_id)
        friends_to_invite = User.query.filter(User.id.in_(friends_subquery), User.id.notin_(members_subquery)).all()
        
    return render_template("pub.html", pub=pub_info, canvas=pub_info.canvas, chat=chat_display_data, friends=friends_to_invite)

@app.route("/invite_to_pub/<int:pub_id>", methods=["POST"])
@login_required
def invite_to_pub(pub_id):
    pub_info = Pub.query.get_or_404(pub_id)
    if pub_info.owner_id != session["user_id"]: return apology("Only the pub owner can invite friends", 403)
    
    friend_id = request.form.get("friend_id")
    if not friend_id: return apology("No friend selected", 400)
    
    if not PubMember.query.filter_by(pub_id=pub_id, user_id=friend_id).first():
        db.session.add(PubMember(pub_id=pub_id, user_id=friend_id))
        db.session.commit()
        flash("Friend invited to the pub!")
    else: flash("This user is already a member.")
        
    return redirect(f"/pub/{pub_id}")

@app.route("/delete_pub/<int:pub_id>", methods=["POST"])
@login_required
def delete_pub(pub_id):
    pub_info = Pub.query.get_or_404(pub_id)
    if pub_info.owner_id != session["user_id"]: return apology("You do not have permission to delete this pub.", 403)
    
    ChatMessage.query.filter_by(pub_id=pub_id).delete()
    db.session.delete(pub_info)
    db.session.commit()
    flash("Pub and all its data have been permanently deleted.")
    return redirect("/dashboard")

@app.route("/canvas_preview/<int:canvas_id>.png")
def canvas_preview(canvas_id):
    canvas = Canvas.query.get(canvas_id)
    if not canvas: return apology("Canvas not found", 404)
    width, height, pixels_json = canvas.width, canvas.height, canvas.canvas_data
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    try:
        pixels = json.loads(pixels_json)
        for y, row in enumerate(pixels):
            for x, color in enumerate(row):
                if color and color != '#FFFFFF': draw.point((x, y), fill=color)
    except: pass
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return Response(img_io.getvalue(), mimetype='image/png')

@app.route("/avatar/<int:user_id>.png")
def avatar(user_id):
    user = User.query.get(user_id)
    pixel_data_json = user.avatar_data if user else None
    AVATAR_SIZE, PIXEL_SIZE = 32, 10
    img_size = AVATAR_SIZE * PIXEL_SIZE
    img = Image.new('RGB', (img_size, img_size), color='#dddddd')
    draw = ImageDraw.Draw(img)
    if pixel_data_json:
        try:
            pixel_data = json.loads(pixel_data_json)
            for y, row in enumerate(pixel_data):
                for x, color in enumerate(row):
                    if color and color != '#FFFFFF': draw.rectangle([x*PIXEL_SIZE, y*PIXEL_SIZE, (x+1)*PIXEL_SIZE-1, (y+1)*PIXEL_SIZE-1], fill=color)
        except: pass
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    response = Response(img_io.getvalue(), mimetype='image/png')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    user = User.query.get(session["user_id"])
    if request.method == "POST":
        avatar_data = request.form.get("avatar_data")
        if not avatar_data: return apology("No avatar data received", 400)
        try: json.loads(avatar_data)
        except: return apology("Invalid avatar data format", 400)
        user.avatar_data = avatar_data
        db.session.commit()
        flash("Avatar updated successfully!")
        return redirect("/settings")
    else:
        current_avatar_data = user.avatar_data or 'null'
        return render_template("settings.html", current_avatar_data=current_avatar_data)

@app.route("/friends")
@login_required
def friends():
    user_id = session["user_id"]
    friends_list = User.query.join(Friendship, or_(User.id == Friendship.user_one_id, User.id == Friendship.user_two_id)).filter(or_(Friendship.user_one_id == user_id, Friendship.user_two_id == user_id), Friendship.status == 'accepted', User.id != user_id).all()
    pending_received_query = db.session.query(Friendship, User).join(User, Friendship.action_user_id == User.id).filter(or_(Friendship.user_one_id == user_id, Friendship.user_two_id == user_id), Friendship.status == 'pending', Friendship.action_user_id != user_id).all()
    
    existing_relations = db.session.query(Friendship.user_one_id).filter(Friendship.user_two_id == user_id).union(db.session.query(Friendship.user_two_id).filter(Friendship.user_one_id == user_id))
    other_users = User.query.filter(User.id != user_id, User.id != 0, User.id.notin_(existing_relations)).all()

    return render_template("friends.html", friends=friends_list, pending_received=pending_received_query, other_users=other_users)

@app.route("/send_request/<int:recipient_id>", methods=["POST"])
@login_required
def send_request(recipient_id):
    sender_id = session["user_id"]
    if sender_id == recipient_id: return apology("You cannot send a friend request to yourself.", 400)
    user_one, user_two = min(sender_id, recipient_id), max(sender_id, recipient_id)
    if Friendship.query.filter_by(user_one_id=user_one, user_two_id=user_two).first():
        flash("A friend request is already pending or you are already friends.")
        return redirect("/friends")
    new_request = Friendship(user_one_id=user_one, user_two_id=user_two, status='pending', action_user_id=sender_id)
    db.session.add(new_request)
    db.session.commit()
    flash("Friend request sent!")
    return redirect("/friends")

@app.route("/accept_request/<int:friendship_id>", methods=["POST"])
@login_required
def accept_request(friendship_id):
    user_id = session['user_id']
    friendship = Friendship.query.filter_by(id=friendship_id).filter(or_(Friendship.user_one_id == user_id, Friendship.user_two_id == user_id), Friendship.action_user_id != user_id).first()
    if not friendship: return apology("Invalid request", 403)
    friendship.status = 'accepted'
    db.session.commit()
    flash("Friend request accepted!")
    return redirect("/friends")

@app.route("/decline_request/<int:friendship_id>", methods=["POST"])
@login_required
def decline_request(friendship_id):
    user_id = session['user_id']
    friendship = Friendship.query.filter_by(id=friendship_id).filter(or_(Friendship.user_one_id == user_id, Friendship.user_two_id == user_id), Friendship.action_user_id != user_id).first()
    if not friendship: return apology("Invalid request", 403)
    db.session.delete(friendship)
    db.session.commit()
    flash("Friend request declined.")
    return redirect("/friends")

@app.route("/unfriend/<int:friend_id>", methods=["POST"])
@login_required
def unfriend(friend_id):
    user_id = session["user_id"]
    user_one = min(user_id, friend_id)
    user_two = max(user_id, friend_id)
    friendship = Friendship.query.filter_by(user_one_id=user_one, user_two_id=user_two, status='accepted').first()
    if friendship:
        db.session.delete(friendship)
        db.session.commit()
        flash("Friend removed.")
    return redirect("/friends")

# --- Authentication Routes ---
@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        username, password = request.form.get("username"), request.form.get("password")
        if not username or not password: return apology("must provide username and password", 400)
        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.hash, password):
            return apology("invalid username and/or password", 403)
        session["user_id"], session["username"], session["role"] = user.id, user.username, user.role
        flash("Logged in successfully!")
        return redirect("/")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username, password, confirmation = request.form.get("username"), request.form.get("password"), request.form.get("confirmation")
        if not username or not password or not confirmation: return apology("must fill all fields", 400)
        if password != confirmation: return apology("passwords do not match", 400)
        if User.query.filter_by(username=username).first(): return apology("username already exists", 400)
        
        new_user = User(username=username, hash=generate_password_hash(password), avatar_data=json.dumps([['#FFFFFF' for _ in range(32)] for _ in range(32)]))
        db.session.add(new_user)
        db.session.commit()
        
        session["user_id"], session["username"], session["role"] = new_user.id, new_user.username, new_user.role
        flash("Registered successfully!")
        return redirect("/")
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect("/login")

@app.route("/guest_login", methods=["POST"])
def guest_login():
    session.clear()
    session["guest_name"] = f"Guest{random.randint(1000, 9999)}"
    lobby = Pub.query.filter_by(name='The Guest Pub').first()
    if lobby:
        return redirect(f"/pub/{lobby.id}")
    return apology("Main community hub not found.", 500)

# --- SocketIO Handlers ---
@socketio.on('join_pub')
def handle_join_pub(data):
    if 'user_id' not in session and 'guest_name' not in session: return
    join_room(f"pub_{data['pub_id']}")

@socketio.on('place_pixel')
def handle_place_pixel(data):
    if 'user_id' not in session and 'guest_name' not in session: return
    emit('pixel_placed', data, room=f"pub_{data.get('pub_id')}", include_self=False)

@socketio.on('save_canvas_state')
def handle_save_canvas_state(data):
    if 'user_id' not in session and 'guest_name' not in session: return
    canvas_id, canvas_data = data.get('canvas_id'), data.get('canvas_data')
    if not canvas_id or not canvas_data: return
    canvas = Canvas.query.get(canvas_id)
    if canvas:
        canvas.canvas_data = json.dumps(canvas_data)
        db.session.commit()
        print(f"Canvas {canvas.id} saved.")
    
@socketio.on('log_pixel_history')
def handle_log_pixel_history(data):
    user_id = session.get('user_id')
    if not user_id: return
    canvas_id, pixels = data.get('canvas_id'), data.get('pixels')
    if not canvas_id or not pixels: return
    for pixel in pixels:
        history_entry = PixelHistory(canvas_id=canvas_id, x=pixel['x'], y=pixel['y'], modifier_id=user_id, color=pixel['color'])
        db.session.add(history_entry)
    db.session.commit()
    print(f"Logged {len(pixels)} pixels to history for canvas {canvas_id} by user {user_id}")

@socketio.on('request_history')
def handle_request_history(data):
    canvas_id, x, y = data.get('canvas_id'), data.get('x'), data.get('y')
    history_entry = PixelHistory.query.filter_by(canvas_id=canvas_id, x=x, y=y).order_by(PixelHistory.timestamp.desc()).first()
    if history_entry:
        emit('history_response', {'username': history_entry.user.username, 'timestamp': history_entry.timestamp.isoformat()})
    else:
        emit('history_response', {'username': 'N/A', 'timestamp': 'Never modified'})

@socketio.on('send_message')
def handle_send_message(data):
    user_id = session.get('user_id')
    username = session.get('username') or session.get('guest_name')
    if not username: return
    pub_id, content = data.get('pub_id'), data.get('content', '').strip()
    if not (1 <= len(content) <= 250): return
    
    user_id_for_db = user_id if user_id is not None else 0
    new_message = ChatMessage(pub_id=pub_id, user_id=user_id_for_db, content=content)
    db.session.add(new_message)
    
    message_count = ChatMessage.query.filter_by(pub_id=pub_id).count()
    if message_count > 100:
        oldest_message = ChatMessage.query.filter_by(pub_id=pub_id).order_by(ChatMessage.timestamp.asc()).first()
        db.session.delete(oldest_message)
    
    db.session.commit()
    message_data = {'username': username, 'avatar_id': user_id_for_db, 'content': content}
    emit('new_message', message_data, room=f"pub_{pub_id}")

# This block should be at the very end of the file
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Initialization logic for community pubs
        if not User.query.get(0):
            guest = User(id=0, username='__GUEST__', hash='', role='guest')
            db.session.add(guest)
        
        community_pubs_data = [("The Guest Pub", 128, 128), ("The 8-Bit Bar", 48, 48), ("The Doodle Den", 64, 32), ("The Canvas Corner", 128, 128)]
        for name, width, height in community_pubs_data:
            if not Pub.query.filter_by(name=name, owner_id=None).first():
                canvas = Canvas(name=f"Community: {name}", width=width, height=height, canvas_data=json.dumps([['#FFFFFF' for _ in range(width)] for _ in range(height)]))
                pub = Pub(name=name, is_private=False, canvas=canvas)
                db.session.add(pub)
        
        db.session.commit()
        
    socketio.run(app, debug=True)
