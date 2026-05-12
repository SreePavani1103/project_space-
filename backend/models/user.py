"""
User model.

Includes is_admin flag for the admin panel (Module 9).
Password is stored hashed via werkzeug.
GitHub OAuth users have no password — password_hash is nullable for them.
"""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from backend.extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(80), nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)   # nullable for OAuth users
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_synced_at = db.Column(db.DateTime, nullable=True)

    # GitHub OAuth fields
    github_id = db.Column(db.String(64), unique=True, nullable=True, index=True)
    avatar_url = db.Column(db.String(512), nullable=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @classmethod
    def get_or_create_from_github(cls, github_profile: dict):
        """Find existing user by github_id or email, or create a new one."""
        github_id = str(github_profile["id"])
        email = github_profile.get("email") or f"gh_{github_id}@noreply.github.com"
        name = github_profile.get("name") or github_profile.get("login", "GitHub User")
        avatar_url = github_profile.get("avatar_url", "")

        # Try by github_id first (most reliable)
        user = cls.query.filter_by(github_id=github_id).first()
        if user:
            # Refresh avatar in case it changed
            user.avatar_url = avatar_url
            return user, False  # (user, created)

        # Try by email (account merge — existing email/password user logs in via GitHub)
        user = cls.query.filter_by(email=email).first()
        if user:
            user.github_id = github_id
            user.avatar_url = avatar_url
            return user, False

        # Create new user
        user = cls(
            email=email,
            name=name,
            github_id=github_id,
            avatar_url=avatar_url,
        )
        db.session.add(user)
        return user, True  # (user, created)

    def __repr__(self) -> str:
        return f"<User {self.email}{' [admin]' if self.is_admin else ''}>"


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))
