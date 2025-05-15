# Routes for Smart Recommendations

from flask import Blueprint, request, jsonify
from ..models import db
from ..models.user import User
from ..models.content import ContentItem, Tag
from ..models.recommendation import UserContentInteraction, UserRecommendation, UserLearningGoal
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
import datetime

recommendation_bp = Blueprint("recommendation_bp", __name__, url_prefix="/api/recommendations")

# Helper function to get current user (placeholder - same as in other route files)
def get_current_user_id():
    user = User.query.first()
    if user:
        return user.id
    print("WARN: No users found, creating a dummy user with id 1 for testing recommendations.")
    dummy_user = User(username="dummy_reco_user", email="dummy_reco@example.com", password_hash="dummy")
    db.session.add(dummy_user)
    try:
        db.session.commit()
        return dummy_user.id
    except Exception as e:
        db.session.rollback()
        print(f"Error creating dummy user for recommendations: {e}")
        return None

# --- User Content Interaction Routes ---
@recommendation_bp.route("/interactions", methods=["POST"])
def log_user_interaction():
    data = request.get_json()
    user_id = get_current_user_id() # In a real app, this would be the authenticated user

    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401
    if not data or not data.get("content_item_id") or not data.get("interaction_type"):
        return jsonify({"error": "Missing user_id, content_item_id, or interaction_type"}), 400

    interaction = UserContentInteraction(
        user_id=user_id,
        content_item_id=data["content_item_id"],
        interaction_type=data["interaction_type"],
        interaction_value=data.get("interaction_value")
    )
    try:
        db.session.add(interaction)
        db.session.commit()
        return jsonify({"message": "Interaction logged", "id": interaction.id}), 201
    except IntegrityError as e:
        db.session.rollback()
        # Check if it's a foreign key constraint violation
        if "FOREIGN KEY constraint failed" in str(e) or "a foreign key constraint fails" in str(e).lower():
            if not User.query.get(user_id):
                 return jsonify({"error": "User not found for interaction logging."}), 404
            if not ContentItem.query.get(data["content_item_id"]):
                 return jsonify({"error": "Content item not found for interaction logging."}), 404
        return jsonify({"error": "Database integrity error logging interaction", "details": str(e)}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Could not log interaction", "details": str(e)}), 500

# --- User Recommendation Routes ---
@recommendation_bp.route("/user/<int:user_id>", methods=["GET"])
def get_user_recommendations(user_id):
    # This is a placeholder for a more sophisticated recommendation logic.
    # For now, it might fetch pre-calculated recommendations or use a simple logic.

    # Example: Get active pre-calculated recommendations
    recs = UserRecommendation.query.filter_by(user_id=user_id, is_active=True)\
        .options(joinedload(UserRecommendation.recommended_content_item).joinedload(ContentItem.tags))\
        .order_by(UserRecommendation.score.desc(), UserRecommendation.generated_at.desc())\
        .limit(10).all()

    if recs:
        output = [
            {
                "recommendation_id": rec.id,
                "content_item_id": rec.recommended_content_item_id,
                "title": rec.recommended_content_item.title,
                "description": rec.recommended_content_item.description,
                "content_type": rec.recommended_content_item.content_type,
                "tags": [tag.name for tag in rec.recommended_content_item.tags],
                "recommendation_source": rec.recommendation_source,
                "score": rec.score,
                "generated_at": rec.generated_at.isoformat()
            } for rec in recs
        ]
        return jsonify(output), 200

    # Fallback: Simple content-based recommendation (e.g., based on user's liked tags or recent interactions)
    # This requires more complex logic:    
    # 1. Get user's recent positive interactions (e.g., likes, completions).
    # 2. Extract features (e.g., tags) from those interacted items.
    # 3. Find other content items with similar features, not yet interacted with by the user.
    # This is a simplified version:
    user_interactions = UserContentInteraction.query.filter_by(user_id=user_id)\
        .filter(UserContentInteraction.interaction_type.in_(["like", "completed_quiz", "rated_5_stars"]))\
        .order_by(UserContentInteraction.timestamp.desc())\
        .limit(20).all()

    if not user_interactions:
        # If no interactions, recommend popular or recent items (very basic)
        popular_items = ContentItem.query.options(joinedload(ContentItem.tags))\
            .order_by(ContentItem.updated_at.desc()).limit(5).all()
        output = [
            {
                "content_item_id": item.id,
                "title": item.title,
                "description": item.description,
                "content_type": item.content_type,
                "tags": [tag.name for tag in item.tags],
                "recommendation_source": "popular_or_recent",
            } for item in popular_items
        ]
        return jsonify(output), 200

    # Simple: Recommend items with tags similar to recently liked items
    interacted_content_ids = {interaction.content_item_id for interaction in user_interactions}
    liked_tags = set()
    for interaction in user_interactions:
        content_item = ContentItem.query.options(joinedload(ContentItem.tags)).get(interaction.content_item_id)
        if content_item:
            for tag in content_item.tags:
                liked_tags.add(tag.name)
    
    if not liked_tags:
        return jsonify({"message": "Not enough interaction data to generate recommendations based on tags."}), 200

    # Find items with these tags, excluding already interacted items
    recommended_items_query = ContentItem.query\
        .join(ContentItem.tags)\
        .filter(Tag.name.in_(list(liked_tags)))\
        .filter(ContentItem.id.notin_(list(interacted_content_ids)))\
        .options(joinedload(ContentItem.tags))
    
    # Add distinct to avoid duplicate content items if they have multiple matching tags
    recommended_items_query = recommended_items_query.distinct()
    recommended_items = recommended_items_query.limit(10).all()

    output = [
        {
            "content_item_id": item.id,
            "title": item.title,
            "description": item.description,
            "content_type": item.content_type,
            "tags": [tag.name for tag in item.tags],
            "recommendation_source": "simple_content_based_tags",
        } for item in recommended_items
    ]
    return jsonify(output), 200

# --- User Learning Goal Routes ---
@recommendation_bp.route("/goals/user/<int:user_id>", methods=["POST"])
def create_user_learning_goal(user_id):
    data = request.get_json()
    # In a real app, ensure the authenticated user matches user_id or is an admin
    auth_user_id = get_current_user_id()
    if auth_user_id != user_id:
        # This check might be too strict depending on your app's logic (e.g. admin setting goals for user)
        # For now, let's assume user can only set their own goals.
        # return jsonify({"error": "User mismatch or not authorized"}), 403
        pass # Allow for now, but this needs proper authz

    if not data or not data.get("goal_description"):
        return jsonify({"error": "Missing goal_description"}), 400

    goal = UserLearningGoal(
        user_id=user_id,
        goal_description=data["goal_description"],
        priority=data.get("priority", 0)
    )
    try:
        db.session.add(goal)
        db.session.commit()
        return jsonify({"message": "Learning goal created", "id": goal.id}), 201
    except IntegrityError as e:
        db.session.rollback()
        if "FOREIGN KEY constraint failed" in str(e) or "a foreign key constraint fails" in str(e).lower():
             if not User.query.get(user_id):
                 return jsonify({"error": "User not found for learning goal."}), 404
        return jsonify({"error": "Database integrity error creating learning goal", "details": str(e)}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Could not create learning goal", "details": str(e)}), 500

@recommendation_bp.route("/goals/user/<int:user_id>", methods=["GET"])
def get_user_learning_goals(user_id):
    # Auth check: ensure authenticated user matches user_id or is admin
    goals = UserLearningGoal.query.filter_by(user_id=user_id).order_by(UserLearningGoal.priority.desc(), UserLearningGoal.created_at.desc()).all()
    output = [
        {
            "id": goal.id,
            "user_id": goal.user_id,
            "goal_description": goal.goal_description,
            "priority": goal.priority,
            "is_achieved": goal.is_achieved,
            "created_at": goal.created_at.isoformat(),
            "updated_at": goal.updated_at.isoformat()
        } for goal in goals
    ]
    return jsonify(output), 200

@recommendation_bp.route("/goals/<int:goal_id>", methods=["PUT"])
def update_user_learning_goal(goal_id):
    goal = UserLearningGoal.query.get(goal_id)
    if not goal:
        return jsonify({"error": "Learning goal not found"}), 404

    # Auth check: ensure authenticated user owns this goal or is admin
    auth_user_id = get_current_user_id()
    if auth_user_id != goal.user_id:
        # return jsonify({"error": "Not authorized to update this goal"}), 403
        pass # Allow for now

    data = request.get_json()
    goal.goal_description = data.get("goal_description", goal.goal_description)
    goal.priority = data.get("priority", goal.priority)
    goal.is_achieved = data.get("is_achieved", goal.is_achieved)
    goal.updated_at = datetime.datetime.utcnow()

    try:
        db.session.commit()
        return jsonify({"message": "Learning goal updated", "id": goal.id}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Could not update learning goal", "details": str(e)}), 500

@recommendation_bp.route("/goals/<int:goal_id>", methods=["DELETE"])
def delete_user_learning_goal(goal_id):
    goal = UserLearningGoal.query.get(goal_id)
    if not goal:
        return jsonify({"error": "Learning goal not found"}), 404

    # Auth check: ensure authenticated user owns this goal or is admin
    auth_user_id = get_current_user_id()
    if auth_user_id != goal.user_id:
        # return jsonify({"error": "Not authorized to delete this goal"}), 403
        pass # Allow for now

    try:
        db.session.delete(goal)
        db.session.commit()
        return jsonify({"message": "Learning goal deleted"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Could not delete learning goal", "details": str(e)}), 500

# A more advanced recommendation generation endpoint could be added here.
# This would likely be a background task or a more complex API call.
# For example: /api/recommendations/generate/user/<int:user_id>

