# Models for Smart Recommendations

from sqlalchemy.dialects.mysql import INTEGER
from . import db # Assuming db is initialized in __init__.py of the models directory or src
import datetime

# This table can store various user interactions with content that can be used for recommendations.
# Examples: view, like, complete, explicit rating.
class UserContentInteraction(db.Model):
    __tablename__ = "user_content_interactions"
    id = db.Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    user_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("users.id"), nullable=False)
    content_item_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("content_items.id"), nullable=False)
    # e.g., "view", "like", "completed_quiz", "rated_5_stars", "spent_30_mins"
    interaction_type = db.Column(db.String(100), nullable=False)
    interaction_value = db.Column(db.String(255), nullable=True) # e.g., rating value, time spent
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship("User", backref=db.backref("content_interactions", lazy="dynamic"))
    content_item = db.relationship("ContentItem", backref=db.backref("user_interactions", lazy="dynamic"))

    def __repr__(self):
        return f"<UserContentInteraction User {self.user_id} - Content {self.content_item_id} - Type {self.interaction_type}>"

# This table could store pre-calculated recommendations for users.
# This is an optional optimization; recommendations can also be generated on-the-fly.
class UserRecommendation(db.Model):
    __tablename__ = "user_recommendations"
    id = db.Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    user_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("users.id"), nullable=False)
    recommended_content_item_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("content_items.id"), nullable=False)
    # e.g., "collaborative_filtering", "content_based", "trending"
    recommendation_source = db.Column(db.String(100), nullable=True) 
    score = db.Column(db.Float, nullable=True) # Confidence score of the recommendation
    generated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    # Recommendation can be marked as seen or interacted with to avoid re-recommending immediately
    is_active = db.Column(db.Boolean, default=True)

    user = db.relationship("User", backref=db.backref("recommendations", lazy="dynamic"))
    recommended_content_item = db.relationship("ContentItem")

    def __repr__(self):
        return f"<UserRecommendation User {self.user_id} - Recommends Content {self.recommended_content_item_id}>"

# To make content-based recommendations, we might need to extract features from content.
# Tags are already in content.py. We could add more specific features here if needed,
# or rely on analyzing markdown_content, description, etc.
# For now, we'll assume existing fields and tags are sufficient for initial content-based filtering.

# Example: A model to store user learning paths or goals, which can heavily influence recommendations.
class UserLearningGoal(db.Model):
    __tablename__ = "user_learning_goals"
    id = db.Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    user_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("users.id"), nullable=False)
    # Could be a tag_id, a specific skill, or a free-text description
    goal_description = db.Column(db.Text, nullable=False) 
    # target_skill_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("skills.id"), nullable=True)
    # target_tag_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("tags.id"), nullable=True)
    priority = db.Column(db.Integer, default=0) # 0 = normal, higher = more important
    is_achieved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = db.relationship("User", backref=db.backref("learning_goals", lazy="dynamic"))
    # skill = db.relationship("Skill")
    # tag = db.relationship("Tag")

    def __repr__(self):
        return f"<UserLearningGoal User {self.user_id} - Goal: {self.goal_description[:50]}...>"


