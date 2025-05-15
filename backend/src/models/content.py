# Models for Content, Content Versions, and Tags

from sqlalchemy.dialects.mysql import INTEGER
from . import db # Assuming db is initialized in __init__.py of the models directory or src
import datetime

class ContentTag(db.Model):
    __tablename__ = "content_tags"
    content_item_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("content_items.id"), primary_key=True)
    tag_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("tags.id"), primary_key=True)

class Tag(db.Model):
    __tablename__ = "tags"
    id = db.Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    # Relationship to ContentItem through ContentTag
    content_items = db.relationship("ContentItem", secondary="content_tags", back_populates="tags")

    def __repr__(self):
        return f"<Tag {self.name}>"

class ContentItem(db.Model):
    __tablename__ = "content_items"
    id = db.Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    # Example: 'article', 'video', 'quiz'. Consider an Enum or a separate ContentType table for more complex scenarios.
    content_type = db.Column(db.String(50), nullable=False, default="article") 
    created_by_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("users.id"), nullable=False)
    entity_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("entities.id"), nullable=True) # Optional link to an entity
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationship to User (creator)
    creator = db.relationship("User", backref=db.backref("created_content_items", lazy="dynamic"))
    # Relationship to Entity
    entity = db.relationship("Entity", backref=db.backref("content_items", lazy="dynamic"))
    
    # Relationship to ContentVersion
    versions = db.relationship("ContentVersion", back_populates="content_item", lazy="dynamic", cascade="all, delete-orphan")
    current_version_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("content_versions.id"), nullable=True)
    current_version = db.relationship("ContentVersion", foreign_keys=[current_version_id], post_update=True)

    # Relationship to Tag through ContentTag
    tags = db.relationship("Tag", secondary="content_tags", back_populates="content_items")

    def __repr__(self):
        return f"<ContentItem {self.title}>"

class ContentVersion(db.Model):
    __tablename__ = "content_versions"
    id = db.Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    content_item_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("content_items.id"), nullable=False)
    version_number = db.Column(db.Integer, nullable=False, default=1)
    markdown_content = db.Column(db.Text, nullable=True) # For articles, supporting LaTeX within Markdown
    # video_url = db.Column(db.String(512), nullable=True) # If type is video
    # quiz_data = db.Column(db.JSON, nullable=True) # If type is quiz, stores quiz structure or link to Quiz model
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    created_by_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("users.id"), nullable=False)
    is_published = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True) # Optional notes for this version

    # Relationship to ContentItem
    content_item = db.relationship("ContentItem", back_populates="versions", foreign_keys=[content_item_id])
    # Relationship to User (version creator)
    version_creator = db.relationship("User", backref=db.backref("created_content_versions", lazy="dynamic"))

    def __repr__(self):
        return f"<ContentVersion {self.content_item.title} - v{self.version_number}>"

