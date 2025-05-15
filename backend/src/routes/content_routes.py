# Routes for Content Management (ContentItems and ContentVersions)

from flask import Blueprint, request, jsonify
from ..models import db
from ..models.content import ContentItem, ContentVersion, Tag, ContentTag # Assuming Tag and ContentTag are in content.py
from ..models.user import User # For created_by_id
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
import datetime

content_bp = Blueprint("content_bp", __name__, url_prefix="/api/content")

# Helper function to get current user (placeholder)
# In a real app, this would come from an auth system (e.g., JWT token)
def get_current_user_id():
    # For now, let's assume user_id 1 exists and is the creator
    # This should be replaced with actual authentication logic
    user = User.query.first()
    if user:
        return user.id
    # Create a dummy user if none exists, for testing purposes only
    # In a real scenario, user creation would be part of auth routes
    print("WARN: No users found, creating a dummy user with id 1 for testing content creation.")
    dummy_user = User(username="dummy_content_creator", email="dummy_content@example.com", password_hash="dummy")
    db.session.add(dummy_user)
    try:
        db.session.commit()
        print(f"Dummy user created with id: {dummy_user.id}")
        return dummy_user.id
    except Exception as e:
        db.session.rollback()
        print(f"Error creating dummy user: {e}")
        return None

@content_bp.route("/items", methods=["POST"])
def create_content_item():
    data = request.get_json()
    if not data or not data.get("title") or not data.get("content_type"):
        return jsonify({"error": "Missing title or content_type"}), 400

    creator_id = get_current_user_id()
    if not creator_id:
        return jsonify({"error": "Could not determine creator. User authentication needed."}), 500

    new_item = ContentItem(
        title=data["title"],
        description=data.get("description"),
        content_type=data["content_type"],
        created_by_id=creator_id,
        entity_id=data.get("entity_id")
    )

    tag_names = data.get("tags", [])
    if tag_names:
        for tag_name in tag_names:
            tag = Tag.query.filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.session.add(tag)
            new_item.tags.append(tag)

    try:
        db.session.add(new_item)
        db.session.commit()
        return jsonify({"message": "Content item created", "id": new_item.id}), 201
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "Database integrity error", "details": str(e)}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Could not create content item", "details": str(e)}), 500

@content_bp.route("/items", methods=["GET"])
def get_content_items():
    items = ContentItem.query.options(joinedload(ContentItem.tags), joinedload(ContentItem.current_version)).all()
    output = []
    for item in items:
        item_data = {
            "id": item.id,
            "title": item.title,
            "description": item.description,
            "content_type": item.content_type,
            "created_by_id": item.created_by_id,
            "entity_id": item.entity_id,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
            "tags": [tag.name for tag in item.tags],
            "current_version_id": item.current_version_id,
            "current_version_number": item.current_version.version_number if item.current_version else None
        }
        output.append(item_data)
    return jsonify(output), 200

@content_bp.route("/items/<int:item_id>", methods=["GET"])
def get_content_item(item_id):
    item = ContentItem.query.options(joinedload(ContentItem.tags), joinedload(ContentItem.current_version)).get(item_id)
    if not item:
        return jsonify({"error": "Content item not found"}), 404
    
    item_data = {
        "id": item.id,
        "title": item.title,
        "description": item.description,
        "content_type": item.content_type,
        "created_by_id": item.created_by_id,
        "entity_id": item.entity_id,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "tags": [tag.name for tag in item.tags],
        "current_version_id": item.current_version_id,
        "current_version_markdown": item.current_version.markdown_content if item.current_version else None,
        "current_version_number": item.current_version.version_number if item.current_version else None
    }
    return jsonify(item_data), 200

@content_bp.route("/items/<int:item_id>", methods=["PUT"])
def update_content_item(item_id):
    item = ContentItem.query.get(item_id)
    if not item:
        return jsonify({"error": "Content item not found"}), 404

    data = request.get_json()
    item.title = data.get("title", item.title)
    item.description = data.get("description", item.description)
    item.content_type = data.get("content_type", item.content_type)
    item.entity_id = data.get("entity_id", item.entity_id)
    item.updated_at = datetime.datetime.utcnow()

    if "tags" in data:
        item.tags.clear() # Clear existing tags
        tag_names = data.get("tags", [])
        for tag_name in tag_names:
            tag = Tag.query.filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.session.add(tag)
            item.tags.append(tag)

    try:
        db.session.commit()
        return jsonify({"message": "Content item updated", "id": item.id}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Could not update content item", "details": str(e)}), 500

@content_bp.route("/items/<int:item_id>", methods=["DELETE"])
def delete_content_item(item_id):
    item = ContentItem.query.get(item_id)
    if not item:
        return jsonify({"error": "Content item not found"}), 404
    try:
        db.session.delete(item)
        db.session.commit()
        return jsonify({"message": "Content item deleted"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Could not delete content item", "details": str(e)}), 500

# --- ContentVersion Routes ---

@content_bp.route("/items/<int:item_id>/versions", methods=["POST"])
def create_content_version(item_id):
    content_item = ContentItem.query.get(item_id)
    if not content_item:
        return jsonify({"error": "Content item not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing data"}), 400

    creator_id = get_current_user_id()
    if not creator_id:
        return jsonify({"error": "Could not determine creator. User authentication needed."}), 500

    # Determine next version number
    last_version = ContentVersion.query.filter_by(content_item_id=item_id).order_by(ContentVersion.version_number.desc()).first()
    next_version_number = (last_version.version_number + 1) if last_version else 1

    new_version = ContentVersion(
        content_item_id=item_id,
        version_number=next_version_number,
        markdown_content=data.get("markdown_content"),
        created_by_id=creator_id,
        notes=data.get("notes")
    )

    try:
        db.session.add(new_version)
        db.session.commit()
        return jsonify({"message": "Content version created", "id": new_version.id, "version_number": new_version.version_number}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Could not create content version", "details": str(e)}), 500

@content_bp.route("/items/<int:item_id>/versions", methods=["GET"])
def get_content_versions(item_id):
    content_item = ContentItem.query.get(item_id)
    if not content_item:
        return jsonify({"error": "Content item not found"}), 404

    versions = ContentVersion.query.filter_by(content_item_id=item_id).order_by(ContentVersion.version_number.asc()).all()
    output = []
    for version in versions:
        version_data = {
            "id": version.id,
            "version_number": version.version_number,
            "markdown_content_preview": (version.markdown_content[:100] + "...") if version.markdown_content and len(version.markdown_content) > 100 else version.markdown_content,
            "created_at": version.created_at.isoformat(),
            "created_by_id": version.created_by_id,
            "is_published": version.is_published,
            "notes": version.notes
        }
        output.append(version_data)
    return jsonify(output), 200

@content_bp.route("/versions/<int:version_id>", methods=["GET"])
def get_content_version(version_id):
    version = ContentVersion.query.get(version_id)
    if not version:
        return jsonify({"error": "Content version not found"}), 404
    
    version_data = {
        "id": version.id,
        "content_item_id": version.content_item_id,
        "version_number": version.version_number,
        "markdown_content": version.markdown_content,
        "created_at": version.created_at.isoformat(),
        "created_by_id": version.created_by_id,
        "is_published": version.is_published,
        "notes": version.notes
    }
    return jsonify(version_data), 200

@content_bp.route("/versions/<int:version_id>", methods=["PUT"])
def update_content_version(version_id):
    version = ContentVersion.query.get(version_id)
    if not version:
        return jsonify({"error": "Content version not found"}), 404

    data = request.get_json()
    version.markdown_content = data.get("markdown_content", version.markdown_content)
    version.notes = data.get("notes", version.notes)
    
    # Publishing a version updates the ContentItem's current_version_id
    if "is_published" in data:
        version.is_published = data["is_published"]
        if version.is_published:
            content_item = ContentItem.query.get(version.content_item_id)
            if content_item:
                content_item.current_version_id = version.id
                content_item.updated_at = datetime.datetime.utcnow()
            else:
                 return jsonify({"error": "Associated content item not found while trying to publish"}), 500
        # If unpublishing, and this was the current version, set current_version_id to None or to a previous published version.
        # For simplicity, setting to None. A more complex logic could find the latest published one.
        elif not data["is_published"] and version.content_item.current_version_id == version.id:
             version.content_item.current_version_id = None
             version.content_item.updated_at = datetime.datetime.utcnow()

    try:
        db.session.commit()
        return jsonify({"message": "Content version updated", "id": version.id}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Could not update content version", "details": str(e)}), 500

# Note: Deleting specific versions can be complex due to history. 
# Consider soft deletes or archiving instead of hard deletes for versions.
# For now, no DELETE endpoint for individual versions is provided to encourage keeping history.

# --- Tag Routes (Basic) ---
@content_bp.route("/tags", methods=["GET"])
def get_all_tags():
    tags = Tag.query.all()
    return jsonify([{"id": tag.id, "name": tag.name} for tag in tags]), 200

@content_bp.route("/tags", methods=["POST"])
def create_tag():
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "Missing tag name"}), 400
    
    existing_tag = Tag.query.filter_by(name=data["name"]).first()
    if existing_tag:
        return jsonify({"error": "Tag already exists", "id": existing_tag.id}), 409 # Conflict

    new_tag = Tag(name=data["name"])
    try:
        db.session.add(new_tag)
        db.session.commit()
        return jsonify({"message": "Tag created", "id": new_tag.id, "name": new_tag.name}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Could not create tag", "details": str(e)}), 500

