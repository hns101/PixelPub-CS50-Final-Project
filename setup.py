# setup.py
import json
from app import app, db, User, Pub, Canvas

print("STARTING DATABASE SETUP...")

# Use the app's context to interact with the database
with app.app_context():
    # Create all database tables based on the models in app.py
    db.create_all()
    print("Tables created (if they didn't exist).")

    # Initialization logic for the special guest user
    if not User.query.get(0):
        guest = User(id=0, username='__GUEST__', hash='', role='guest')
        db.session.add(guest)
        print("Guest user created.")

    # Initialization logic for community pubs
    community_pubs_data = [("The Guest Pub", 128, 128), ("The 8-Bit Bar", 48, 48), ("The Doodle Den", 64, 32), ("The Canvas Corner", 128, 128)]
    for name, width, height in community_pubs_data:
        if not Pub.query.filter_by(name=name, owner_id=None).first():
            print(f"Creating community pub: {name}...")
            canvas = Canvas(name=f"Community: {name}", width=width, height=height, canvas_data=json.dumps([['#FFFFFF' for _ in range(width)] for _ in range(height)]))
            # We must add and commit the canvas first to get its ID
            db.session.add(canvas)
            db.session.commit()
            
            pub = Pub(name=name, is_private=False, canvas_id=canvas.id)
            db.session.add(pub)
    
    # Commit all changes to the database
    db.session.commit()
    print("Community pubs initialized.")

print("DATABASE SETUP COMPLETE.")