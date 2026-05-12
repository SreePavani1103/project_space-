
from run import app
from backend.extensions import db
from backend.models.user import User
from backend.models.report import Report

with app.app_context():
    db.drop_all()
    db.create_all()
    print("Database schema updated successfully!")
