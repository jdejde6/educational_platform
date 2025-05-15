# /home/ubuntu/educational_platform/backend/educational_platform_backend/src/routes/team_routes.py
from flask import Blueprint, request, jsonify
from ..models.user import db, User # Assuming User model has 'level' and 'specialization' attributes
from ..models.team import Team, Role, TeamMember
from ..models.entity import Entity # If teams are linked to entities
from sqlalchemy.exc import IntegrityError
from datetime import datetime

team_bp = Blueprint("team", __name__, url_prefix="/teams")

# Helper function to get or create a default role
def get_or_create_role(role_name, description=None):
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        role = Role(name=role_name, description=description)
        db.session.add(role)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            role = Role.query.filter_by(name=role_name).first()
    return role

# Pre-populate basic roles
# Role initialization logic has been moved to main.py within app_context

# --- Team (Group) Management ---
@team_bp.route("/", methods=["POST"])
def create_team():
    data = request.get_json()
    name = data.get("name")
    description = data.get("description")
    creator_id = data.get("creator_id") # Should come from authenticated user session
    entity_id = data.get("entity_id") # Optional
    auto_division_criteria = data.get("auto_division_criteria") # e.g., "level:beginner;specialty:math"

    if not name or not creator_id:
        return jsonify({"message": "Team name and creator ID are required"}), 400

    creator = User.query.get(creator_id)
    if not creator:
        return jsonify({"message": "Creator user not found"}), 404

    if Team.query.filter_by(name=name).first():
        return jsonify({"message": "Team with this name already exists"}), 409
    
    entity = None
    if entity_id:
        entity = Entity.query.get(entity_id)
        if not entity:
            return jsonify({"message": "Associated entity not found"}), 404

    new_team = Team(
        name=name,
        description=description,
        creator_id=creator_id,
        entity_id=entity_id,
        auto_division_criteria=auto_division_criteria
    )
    db.session.add(new_team)
    
    owner_role = get_or_create_role("owner")
    if not owner_role:
        return jsonify({"message": "Default owner role not found"}), 500
        
    try:
        db.session.flush()
        team_member_association = TeamMember(
            user_id=creator_id,
            team_id=new_team.id,
            role_id=owner_role.id
        )
        db.session.add(team_member_association)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Failed to create team or assign owner: {str(e)}"}), 500

    return jsonify({"message": "Team created successfully", "team_id": new_team.id}), 201

@team_bp.route("/<int:team_id>", methods=["GET"])
def get_team(team_id):
    team = Team.query.get_or_404(team_id)
    return jsonify({
        "id": team.id,
        "name": team.name,
        "description": team.description,
        "creator_id": team.creator_id,
        "entity_id": team.entity_id,
        "created_at": team.created_at.isoformat(),
        "updated_at": team.updated_at.isoformat(),
        "auto_division_criteria": team.auto_division_criteria
    }), 200

@team_bp.route("/<int:team_id>", methods=["PUT"])
def update_team(team_id):
    team = Team.query.get_or_404(team_id)
    data = request.get_json()
    # Add permission check here

    team.name = data.get("name", team.name)
    team.description = data.get("description", team.description)
    team.auto_division_criteria = data.get("auto_division_criteria", team.auto_division_criteria)
    team.updated_at = datetime.utcnow()
    
    db.session.commit()
    return jsonify({"message": "Team updated successfully"}), 200

@team_bp.route("/<int:team_id>", methods=["DELETE"])
def delete_team(team_id):
    team = Team.query.get_or_404(team_id)
    # Add permission check here

    TeamMember.query.filter_by(team_id=team_id).delete()
    db.session.delete(team)
    db.session.commit()
    return jsonify({"message": "Team and its member associations deleted successfully"}), 200

@team_bp.route("/", methods=["GET"])
def list_teams():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    teams_pagination = Team.query.order_by(Team.name).paginate(page=page, per_page=per_page, error_out=False)
    teams = teams_pagination.items
    return jsonify({
        "teams": [
            {"id": t.id, "name": t.name, "description": t.description, "creator_id": t.creator_id} for t in teams
        ],
        "total_pages": teams_pagination.pages,
        "current_page": teams_pagination.page,
        "total_teams": teams_pagination.total
    }), 200

# --- Team Member Management ---
@team_bp.route("/<int:team_id>/members", methods=["POST"])
def add_team_member(team_id):
    team = Team.query.get_or_404(team_id)
    data = request.get_json()
    user_id = data.get("user_id")
    role_name = data.get("role_name", "member")

    if not user_id:
        return jsonify({"message": "User ID is required"}), 400

    user_to_add = User.query.get(user_id)
    if not user_to_add:
        return jsonify({"message": "User to add not found"}), 404
    
    role = get_or_create_role(role_name)
    if not role:
        return jsonify({"message": f"Role {role_name} not found and could not be created"}), 500

    existing_member = TeamMember.query.filter_by(user_id=user_id, team_id=team_id).first()
    if existing_member:
        return jsonify({"message": "User is already a member of this team"}), 409

    new_member_association = TeamMember(user_id=user_id, team_id=team_id, role_id=role.id)
    db.session.add(new_member_association)
    db.session.commit()
    return jsonify({"message": f"User {user_id} added to team {team_id} as {role.name}"}), 201

@team_bp.route("/<int:team_id>/members/<int:user_id>", methods=["DELETE"])
def remove_team_member(team_id, user_id):
    member_association = TeamMember.query.filter_by(user_id=user_id, team_id=team_id).first()
    if not member_association:
        return jsonify({"message": "User is not a member of this team"}), 404

    db.session.delete(member_association)
    db.session.commit()
    return jsonify({"message": f"User {user_id} removed from team {team_id}"}), 200

@team_bp.route("/<int:team_id>/members", methods=["GET"])
def list_team_members(team_id):
    team = Team.query.get_or_404(team_id)
    members_assoc = team.member_associations.all()
    members_data = []
    for assoc in members_assoc:
        members_data.append({
            "user_id": assoc.user_id,
            "username": assoc.user.username,
            "role": assoc.role.name,
            "joined_at": assoc.joined_at.isoformat()
        })
    return jsonify(members_data), 200

@team_bp.route("/<int:team_id>/members/<int:user_id>/role", methods=["PUT"])
def update_member_role(team_id, user_id):
    data = request.get_json()
    new_role_name = data.get("role_name")

    if not new_role_name:
        return jsonify({"message": "New role name is required"}), 400

    member_association = TeamMember.query.filter_by(user_id=user_id, team_id=team_id).first()
    if not member_association:
        return jsonify({"message": "User is not a member of this team"}), 404

    new_role = Role.query.filter_by(name=new_role_name).first()
    if not new_role:
        return jsonify({"message": f"Role {new_role_name} not found"}), 404
    
    member_association.role_id = new_role.id
    db.session.commit()
    return jsonify({"message": f"User {user_id}'s role in team {team_id} updated to {new_role_name}"}), 200

# --- Automatic Group Division ---
@team_bp.route("/<int:team_id>/auto_divide_members", methods=["POST"])
def auto_divide_members(team_id):
    team = Team.query.get_or_404(team_id)
    if not team.auto_division_criteria:
        return jsonify({"message": "Auto-division criteria not set for this team."}), 400

    # Example criteria: "level:beginner;specialty:programming"
    # This is a placeholder for a more complex logic.
    # You would parse criteria and potentially create sub-teams or assign roles based on user attributes.
    # For now, this is a conceptual endpoint.
    
    # Placeholder: Get all members of the current team
    current_members = TeamMember.query.filter_by(team_id=team_id).all()
    
    # Placeholder: Logic to parse criteria and divide members
    # For example, if criteria is "level:beginner", find all users with level beginner
    # and move them to a new sub-team or assign a specific role.
    # This requires User model to have attributes like 'level' and 'specialization'.
    
    # Example: (Assuming User model has 'level' and 'specialization' fields)
    # criteria_parts = team.auto_division_criteria.split(";")
    # for part in criteria_parts:
    #     key, value = part.split(":")
    #     if key == "level":
    #         # Find users with this level and create/assign to a sub-group
    #         pass 
    #     elif key == "specialty":
    #         # Find users with this specialty and create/assign to a sub-group
    #         pass

    # This is highly dependent on how you want to structure sub-teams and user attributes.
    # For a simple PWA, this might be overly complex unless specifically detailed.

    return jsonify({"message": "Automatic division process initiated (placeholder).", "criteria": team.auto_division_criteria}), 200

# --- Real-time Activity (Placeholder - requires WebSockets like Flask-SocketIO) ---
# This would typically be handled by a separate SocketIO setup.
# @team_bp.route("/<int:team_id>/activity_stream")
# def team_activity_stream(team_id):
# #     # Placeholder for real-time activity updates
# #     # This would involve setting up Flask-SocketIO and emitting events
#     return jsonify({"message": "Activity stream endpoint (requires WebSocket implementation)."}), 501


