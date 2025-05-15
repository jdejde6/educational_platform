# /home/ubuntu/educational_platform/backend/educational_platform_backend/src/models/user.py
from flask_sqlalchemy import SQLAlchemy
import bcrypt

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    # For MFA (TOTP)
    otp_secret = db.Column(db.String(16), nullable=True) # Stores the base32 encoded secret
    is_mfa_enabled = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def check_password(self, password):
        return bcrypt.checkpw(password.encode("utf-8"), self.password_hash.encode("utf-8"))

    def __repr__(self):
        return f'<User {self.username}>'
