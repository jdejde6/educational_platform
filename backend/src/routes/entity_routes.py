# /home/ubuntu/educational_platform/backend/educational_platform_backend/src/routes/entity.py
from flask import Blueprint, request, jsonify, send_file
from ..models.user import db, User # Assuming User model might be needed for owner/permissions
from ..models.entity import Entity, EntityReview
from sqlalchemy import func
import csv
import io
import json
from datetime import datetime

entity_bp = Blueprint("entity", __name__, url_prefix="/entities")

# --- Entity Management ---
@entity_bp.route("/", methods=["POST"])
def create_entity():
    data = request.get_json()
    name = data.get("name")
    description = data.get("description")
    owner_id = data.get("owner_id") # This should ideally come from authenticated user session
    website = data.get("website")
    contact_email = data.get("contact_email")
    logo_url = data.get("logo_url")

    if not name or not owner_id:
        return jsonify({"message": "Entity name and owner ID are required"}), 400

    # Check if owner_id is a valid user
    owner = User.query.get(owner_id)
    if not owner:
        return jsonify({"message": "Owner user not found"}), 404

    if Entity.query.filter_by(name=name).first():
        return jsonify({"message": "Entity with this name already exists"}), 409

    new_entity = Entity(
        name=name,
        description=description,
        owner_id=owner_id,
        website=website,
        contact_email=contact_email,
        logo_url=logo_url
    )
    db.session.add(new_entity)
    db.session.commit()
    return jsonify({"message": "Entity created successfully", "entity_id": new_entity.id}), 201

@entity_bp.route("/<int:entity_id>", methods=["GET"])
def get_entity(entity_id):
    entity = Entity.query.get_or_404(entity_id)
    return jsonify({
        "id": entity.id,
        "name": entity.name,
        "description": entity.description,
        "owner_id": entity.owner_id,
        "website": entity.website,
        "contact_email": entity.contact_email,
        "logo_url": entity.logo_url,
        "member_count": entity.member_count,
        "created_at": entity.created_at.isoformat(),
        "updated_at": entity.updated_at.isoformat()
    }), 200

@entity_bp.route("/<int:entity_id>", methods=["PUT"])
def update_entity(entity_id):
    entity = Entity.query.get_or_404(entity_id)
    data = request.get_json()
    # Add permission check here: only owner or admin should update

    entity.name = data.get("name", entity.name)
    entity.description = data.get("description", entity.description)
    entity.website = data.get("website", entity.website)
    entity.contact_email = data.get("contact_email", entity.contact_email)
    entity.logo_url = data.get("logo_url", entity.logo_url)
    entity.updated_at = datetime.utcnow()
    
    db.session.commit()
    return jsonify({"message": "Entity updated successfully"}), 200

@entity_bp.route("/<int:entity_id>", methods=["DELETE"])
def delete_entity(entity_id):
    entity = Entity.query.get_or_404(entity_id)
    # Add permission check here
    # Also, consider what happens to related data (reviews, courses, members)
    db.session.delete(entity)
    db.session.commit()
    return jsonify({"message": "Entity deleted successfully"}), 200

@entity_bp.route("/", methods=["GET"])
def list_entities():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    entities_pagination = Entity.query.order_by(Entity.name).paginate(page=page, per_page=per_page, error_out=False)
    entities = entities_pagination.items
    return jsonify({
        "entities": [
            {
                "id": e.id, "name": e.name, "description": e.description, 
                "owner_id": e.owner_id, "logo_url": e.logo_url
            } for e in entities
        ],
        "total_pages": entities_pagination.pages,
        "current_page": entities_pagination.page,
        "total_entities": entities_pagination.total
    }), 200

# --- Entity Reviews ---
@entity_bp.route("/<int:entity_id>/reviews", methods=["POST"])
def add_entity_review(entity_id):
    entity = Entity.query.get_or_404(entity_id)
    data = request.get_json()
    user_id = data.get("user_id") # Should come from authenticated user
    rating = data.get("rating")
    comment = data.get("comment")

    if not user_id or rating is None:
        return jsonify({"message": "User ID and rating are required"}), 400
    
    reviewer = User.query.get(user_id)
    if not reviewer:
        return jsonify({"message": "Reviewer user not found"}), 404

    # Optional: Check if user has already reviewed this entity
    existing_review = EntityReview.query.filter_by(entity_id=entity_id, user_id=user_id).first()
    if existing_review:
        return jsonify({"message": "You have already reviewed this entity"}), 409

    new_review = EntityReview(entity_id=entity.id, user_id=user_id, rating=rating, comment=comment)
    db.session.add(new_review)
    db.session.commit()
    return jsonify({"message": "Review added successfully", "review_id": new_review.id}), 201

@entity_bp.route("/<int:entity_id>/reviews", methods=["GET"])
def get_entity_reviews(entity_id):
    entity = Entity.query.get_or_404(entity_id)
    reviews = entity.reviews.order_by(EntityReview.created_at.desc()).all()
    return jsonify([{
        "id": r.id, "user_id": r.user_id, "rating": r.rating, 
        "comment": r.comment, "created_at": r.created_at.isoformat(),
        "username": r.user.username # Assuming User model has username
        } for r in reviews]), 200

# --- Entity Dashboard Data (Example) ---
@entity_bp.route("/<int:entity_id>/dashboard", methods=["GET"])
def get_entity_dashboard(entity_id):
    entity = Entity.query.get_or_404(entity_id)
    # Add permission check

    # Example data points
    total_reviews = entity.reviews.count()
    average_rating = db.session.query(func.avg(EntityReview.rating)).filter(EntityReview.entity_id == entity_id).scalar()
    # member_count is already a field, but could be calculated if using a join table
    # active_courses_count = ... (if Course model exists and is linked)

    return jsonify({
        "entity_id": entity.id,
        "entity_name": entity.name,
        "member_count": entity.member_count, # This should be updated when members join/leave
        "total_reviews": total_reviews,
        "average_rating": float(average_rating) if average_rating else 0,
        # "active_courses_count": active_courses_count 
    }), 200

# --- Data Import/Export ---
@entity_bp.route("/export", methods=["GET"])
# Add authentication/authorization for this route
def export_entities_csv():
    entities = Entity.query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(["id", "name", "description", "owner_id", "website", "contact_email", "logo_url", "member_count", "created_at", "updated_at"])
    # Data
    for entity in entities:
        writer.writerow([
            entity.id, entity.name, entity.description, entity.owner_id, 
            entity.website, entity.contact_email, entity.logo_url, entity.member_count,
            entity.created_at.isoformat(), entity.updated_at.isoformat()
        ])
    
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype="text/csv", as_attachment=True, download_name="entities_export.csv")

@entity_bp.route("/import", methods=["POST"])
# Add authentication/authorization for this route
def import_entities_csv():
    if "file" not in request.files:
        return jsonify({"message": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"message": "No selected file"}), 400
    
    if file and file.filename.endswith(".csv"):
        try:
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_input = csv.DictReader(stream)
            imported_count = 0
            skipped_count = 0
            for row in csv_input:
                # Basic validation and type conversion
                try:
                    owner_id = int(row["owner_id"])
                    name = row["name"]
                    if not name or not User.query.get(owner_id):
                        skipped_count += 1
                        continue
                    
                    # Check for existing entity by name to avoid duplicates
                    if Entity.query.filter_by(name=name).first():
                        skipped_count += 1
                        continue

                    entity = Entity(
                        name=name,
                        description=row.get("description"),
                        owner_id=owner_id,
                        website=row.get("website"),
                        contact_email=row.get("contact_email"),
                        logo_url=row.get("logo_url"),
                        member_count=int(row.get("member_count", 0)),
                        # created_at and updated_at will default or can be parsed if present
                    )
                    db.session.add(entity)
                    imported_count += 1
                except ValueError as ve:
                    print(f"Skipping row due to ValueError: {ve} - Row: {row}")
                    skipped_count += 1
                    continue
                except Exception as e:
                    print(f"Skipping row due to Error: {e} - Row: {row}")
                    skipped_count += 1
                    continue
            
            db.session.commit()
            return jsonify({"message": f"Imported {imported_count} entities, skipped {skipped_count} entities."}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"message": f"Failed to import CSV: {str(e)}"}), 500
    else:
        return jsonify({"message": "Invalid file type, please upload a CSV file"}), 400

# Remember to register this blueprint in your main app factory
# from .routes.entity import entity_bp
# app.register_blueprint(entity_bp)

# And update your main.py to create tables if they don_t exist
# with app.app_context():
#     db.create_all() # This should be handled carefully, migrations are better for production

