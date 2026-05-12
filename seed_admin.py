"""
Seed script — creates the default admin user idempotently.

Usage:
    python seed_admin.py
"""
from backend import create_app
from backend.extensions import db
from backend.models.user import User

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"
ADMIN_NAME = "Admin"


def seed_admin():
    app = create_app()
    with app.app_context():
        existing = User.query.filter_by(email=ADMIN_EMAIL).first()
        if existing:
            print(f"Admin user already exists: {existing.email}")
            return
        admin = User(name=ADMIN_NAME, email=ADMIN_EMAIL, is_admin=True)
        admin.set_password(ADMIN_PASSWORD)
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user created: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")


if __name__ == "__main__":
    seed_admin()
