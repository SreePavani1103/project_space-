"""
Application factory for Skill Synth AI.

The factory pattern keeps the app testable, allows multiple configurations,
and prevents circular imports between extensions and routes.
"""
import os
from flask import Flask

from config import get_config
from backend.extensions import db, login_manager, limiter, oauth
import backend.extensions as extensions
from backend.utils.logger import setup_logging


def create_app(config_class=None):
    """Build and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder="../frontend/templates",
        static_folder="../frontend/static",
        instance_relative_config=True,
    )

    # --- Config ---
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)

    # Make sure instance + upload + chromadb folders exist
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["CHROMA_PERSIST_DIR"], exist_ok=True)

    # --- Logging ---
    setup_logging(app)

    # --- Extensions ---
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login_page"
    login_manager.login_message_category = "info"
    limiter.init_app(app)
    oauth.init_app(app)
    
    # --- Redis & RQ ---
    # BUG 10 FIX: wrapped in try/except so the app starts even if Redis is temporarily down.
    # Without this, a missing Redis crashes the entire app with a ConnectionError at startup.
    try:
        from redis import Redis
        from rq import Queue
        extensions.redis_conn = Redis.from_url(app.config["REDIS_URL"])
        extensions.redis_conn.ping()  # verify connection is actually alive
        extensions.task_queue = Queue("default", connection=extensions.redis_conn)
    except Exception as redis_err:
        app.logger.warning(
            "Redis unavailable (%s). Background analysis will not work. "
            "Start Redis and restart the app to enable analysis.", redis_err
        )
        extensions.redis_conn = None
        extensions.task_queue = None


    # --- GitHub OAuth Provider ---
    client_id = app.config.get("GITHUB_CLIENT_ID")
    client_secret = app.config.get("GITHUB_CLIENT_SECRET")
    
    if not client_id or "your-github" in client_id:
        app.logger.warning("GitHub OAuth credentials not found. 'Login with GitHub' will be disabled.")
    
    oauth.register(
        name="github",
        client_id=client_id,
        client_secret=client_secret,
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "read:user user:email"},
    )

    # --- Models (must import before db.create_all) ---
    from backend.models import user as _user_model  # noqa: F401
    from backend.models import report as _report_model  # noqa: F401
    from backend.models import resume as _resume_model  # noqa: F401

    with app.app_context():
        db.create_all()

    # --- Blueprints ---
    from backend.routes.main import main_bp
    from backend.routes.auth import auth_bp
    from backend.routes.dashboard import dashboard_bp
    from backend.routes.api import api_bp
    from backend.routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)

    # --- Error handlers ---
    from backend.errors import register_error_handlers
    register_error_handlers(app)

    # --- Health check ---
    @app.route("/health")
    def health():
        return {"status": "ok", "module": "full-platform"}

    app.logger.info("Skill Synth AI started in %s mode", app.config.get("ENV", "?"))
    return app
