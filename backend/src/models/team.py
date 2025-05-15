# /home/ubuntu/educational_platform/backend/educational_platform_backend/src/models/team.py
from .user import db, User # Reusing the existing db instance and User model
from datetime import datetime

# Permission Model
class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False) # e.g., "manage_team_settings", "delete_team", "add_member"
    description = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<Permission {self.name}>"

# Role-Permission Association Table
role_permissions = db.Table("role_permissions",
    db.Column("role_id", db.Integer, db.ForeignKey("role.id"), primary_key=True),
    db.Column("permission_id", db.Integer, db.ForeignKey("permission.id"), primary_key=True)
)

# Role Model
class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False) # e.g., "owner", "admin", "member"
    description = db.Column(db.String(255), nullable=True)
    permissions = db.relationship("Permission", secondary=role_permissions, lazy="subquery",
                                  backref=db.backref("roles", lazy=True))

    def __repr__(self):
        return f"<Role {self.name}>"

# Team (or Group) Model
class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    entity_id = db.Column(db.Integer, db.ForeignKey("entity.id"), nullable=True) # Optional: if teams belong to an entity
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    auto_division_criteria = db.Column(db.String(255), nullable=True)

    creator = db.relationship("User", backref=db.backref("created_teams", lazy="dynamic"))
    entity = db.relationship("Entity", backref=db.backref("teams", lazy="dynamic"))

    def __repr__(self):
        return f"<Team {self.name}>"

# TeamMember Association Object (to store role within a team)
class TeamMember(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("team.id"), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("team_associations", lazy="dynamic"))
    team = db.relationship("Team", backref=db.backref("member_associations", lazy="dynamic"))
    role = db.relationship("Role") # Eager load role with permissions

    def __repr__(self):
        return f"<TeamMember User {self.user_id} in Team {self.team_id} as Role {self.role.name if self.role else self.role_id}>"

