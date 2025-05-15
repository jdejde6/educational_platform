# /home/ubuntu/educational_platform/backend/educational_platform_backend/src/models/entity.py
from .user import db # Reusing the existing db instance from user.py
from datetime import datetime

class Entity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False) # Link to the user who owns/created the entity
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Add other relevant fields like website, contact_email, logo_url, etc.
    website = db.Column(db.String(200), nullable=True)
    contact_email = db.Column(db.String(120), nullable=True)
    logo_url = db.Column(db.String(255), nullable=True)
    member_count = db.Column(db.Integer, default=0) # For dashboard analytics
    # Relationships (if needed, e.g., courses offered by this entity)
    # courses = db.relationship("Course", backref="entity", lazy=True)
    # members = db.relationship("User", secondary=entity_members, backref=db.backref("entities_joined", lazy="dynamic")) # Many-to-many for members

    def __repr__(self):
        return f"<Entity {self.name}>"

class EntityReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    entity_id = db.Column(db.Integer, db.ForeignKey("entity.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False) # e.g., 1 to 5 stars
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    entity = db.relationship("Entity", backref=db.backref("reviews", lazy="dynamic"))
    user = db.relationship("User", backref=db.backref("reviews_given", lazy="dynamic"))

    def __repr__(self):
        return f"<EntityReview {self.user_id} for Entity {self.entity_id} - {self.rating} stars>"

# You might need a join table for entity members if users can join multiple entities
# and entities can have multiple users (many-to-many)
# entity_members = db.Table("entity_members",
#     db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
#     db.Column("entity_id", db.Integer, db.ForeignKey("entity.id"), primary_key=True),
#     db.Column("joined_at", db.DateTime, default=datetime.utcnow)
# )

