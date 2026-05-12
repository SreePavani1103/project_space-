"""
Flask extension instances.

Defined here so any module can import them without triggering the
app factory, avoiding circular imports.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from authlib.integrations.flask_client import OAuth
from redis import Redis
from rq import Queue

db = SQLAlchemy()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "60 per hour"])
oauth = OAuth()

# Redis & RQ Queue (initialized in create_app)
redis_conn = None
task_queue = None
