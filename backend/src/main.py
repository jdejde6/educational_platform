import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, jsonify, request # Added request
from flask_socketio import SocketIO
from flask_cors import CORS

from src.models.user import db, User
from src.models.entity import Entity, EntityReview
from src.models.team import Team, Role, TeamMember, Permission, role_permissions
from src.models.content import ContentItem, ContentVersion, Tag, ContentTag
from src.models.quiz import Quiz, Question, AnswerOption, UserQuizAttempt, UserAnswer
from src.models.recommendation import UserContentInteraction, UserRecommendation, UserLearningGoal

from src.routes.auth import auth_bp
from src.routes.entity_routes import entity_bp
from src.routes.team_routes import team_bp, get_or_create_role # Added get_or_create_role
from src.routes.content_routes import content_bp
from src.routes.quiz_routes import quiz_bp
from src.routes.recommendation_routes import recommendation_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), "static"))
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "your_default_secret_key_for_dev_env_shhhh")

CORS(app, resources={r"/api/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

DB_USERNAME = os.getenv("DB_USERNAME", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_HOST = os.getenv("DB_HOST", "localhost")
# استخدام DATABASE_URL من متغيرات البيئة (يوفرها Render)
db_url = os.environ.get('DATABASE_URL')
# تحويل postgres:// إلى postgresql:// إذا لزم الأمر (SQLAlchemy يتطلب postgresql://)
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url


db.init_app(app)
# إنشاء جميع الجداول في قاعدة البيانات
with app.app_context():
    db.create_all()
    print("Database tables created successfully.")

app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(entity_bp, url_prefix="/api/entities")
app.register_blueprint(team_bp, url_prefix="/api/teams")
app.register_blueprint(content_bp, url_prefix="/api/content")
app.register_blueprint(quiz_bp, url_prefix="/api/quizzes")
app.register_blueprint(recommendation_bp, url_prefix="/api/recommendations")

with app.app_context():
    if not User.query.first():
        print("No users found. Creating a default dummy user.")
        default_user = User(username="default_user", email="default@example.com", password_hash="dummy_password") # Proper hashing needed
        db.session.add(default_user)
        try:
            db.session.commit()
            print(f"Default dummy user created with ID: {default_user.id}")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating default dummy user: {e}")

    db.create_all()
    print("Database tables created/verified.")

    print("Initializing default roles...")
    DEFAULT_ROLES = {
        "owner": "Team Owner/Creator with full permissions for the team.",
        "admin": "Team Administrator with most permissions.",
        "moderator": "Team Moderator with content and member management permissions.",
        "member": "Regular team member."
    }
    for role_name, desc in DEFAULT_ROLES.items():
        role = get_or_create_role(role_name, desc)
        if role:
            print(f"Role '{role.name}' ensured/created with ID: {role.id}.")
        else:
            print(f"Warning: Failed to ensure/create role '{role_name}'.")
    print("Default roles initialization complete.")

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return jsonify({"error": "Static folder not configured"}), 404
    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, "index.html")
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, "index.html")
        else:
            return jsonify({"message": "Welcome to the API. Static frontend not found."}), 200

@socketio.on("connect")
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on("disconnect")
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")

@socketio.on("join_team_room")
def handle_join_team_room(data):
    team_id = data.get("team_id")
    if team_id:
        print(f"Client {request.sid} joined room for team {team_id}")
        socketio.emit("room_notification", {"message": f"User {request.sid} joined team {team_id} activity feed."}, room=str(team_id))
    else:
        print("No team_id provided for joining room")

@socketio.on("leave_team_room")
def handle_leave_team_room(data):
    team_id = data.get("team_id")
    if team_id:
        print(f"Client {request.sid} left room for team {team_id}")
        socketio.emit("room_notification", {"message": f"User {request.sid} left team {team_id} activity feed."}, room=str(team_id))
    else:
        print("No team_id provided for leaving room")

if __name__ == "__main__":
    print("Starting Flask-SocketIO server...")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)

