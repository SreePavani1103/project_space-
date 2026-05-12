"""
Authentication routes — register, login, logout, GitHub OAuth.
"""
import logging
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash

from backend.extensions import db, oauth

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET"])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard_page"))
    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET"])
def register_page():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard_page"))
    return render_template("auth/register.html")


@auth_bp.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    from backend.models.user import User
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    user = User(name=name or email.split("@")[0], email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return jsonify({"success": True, "user": {"id": user.id, "name": user.name, "email": user.email}}), 201


@auth_bp.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    from backend.models.user import User
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    login_user(user, remember=data.get("remember", False))
    return jsonify({"success": True, "user": {"id": user.id, "name": user.name, "email": user.email, "is_admin": user.is_admin}})


@auth_bp.route("/api/logout", methods=["POST"])
@login_required
def api_logout():
    logout_user()
    return jsonify({"success": True})


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))


@auth_bp.route("/api/me")
def api_me():
    if current_user.is_authenticated:
        return jsonify({"authenticated": True, "user": {"id": current_user.id, "name": current_user.name, "email": current_user.email, "is_admin": current_user.is_admin, "avatar_url": current_user.avatar_url}})
    return jsonify({"authenticated": False})


# ── GitHub OAuth ──────────────────────────────────────────────────────────────

@auth_bp.route("/github")
def github_login():
    """Redirect user to GitHub for authorization."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard_page"))

    # Check for missing configuration
    from flask import current_app
    client_id = current_app.config.get("GITHUB_CLIENT_ID")
    client_secret = current_app.config.get("GITHUB_CLIENT_SECRET")

    if not client_id or "your-github" in client_id:
        logger.error("GitHub OAuth is not configured: GITHUB_CLIENT_ID is missing or default.")
        flash("GitHub Login is not configured. Please check the .env file.", "error")
        return redirect(url_for("auth.login_page"))

    redirect_uri = url_for("auth.github_callback", _external=True)
    try:
        return oauth.github.authorize_redirect(redirect_uri)
    except Exception as e:
        logger.error("Failed to initiate GitHub OAuth: %s", e)
        flash("Could not connect to GitHub. Please try again later.", "error")
        return redirect(url_for("auth.login_page"))


@auth_bp.route("/github/callback")
def github_callback():
    """Handle the OAuth callback from GitHub."""
    try:
        token = oauth.github.authorize_access_token()
    except Exception as e:
        logger.error("GitHub OAuth error: %s", e)
        flash("GitHub login failed. Please try again.", "error")
        return redirect(url_for("auth.login_page"))

    # Fetch user profile from GitHub API
    resp = oauth.github.get("user", token=token)
    github_profile = resp.json()

    # Fetch primary email if not public
    if not github_profile.get("email"):
        try:
            emails_resp = oauth.github.get("user/emails", token=token)
            emails = emails_resp.json()
            primary = next((e["email"] for e in emails if e.get("primary") and e.get("verified")), None)
            if primary:
                github_profile["email"] = primary
        except Exception:
            pass  # fallback to generated email handled in model

    from backend.models.user import User
    user, created = User.get_or_create_from_github(github_profile)
    # BUG 6 FIX: wrap commit in try/except — race condition (two callbacks from same user)
    # would leave session dirty without rollback, breaking all subsequent DB operations.
    try:
        db.session.commit()
    except Exception as commit_err:
        db.session.rollback()
        logger.error("GitHub OAuth DB commit failed: %s", commit_err)
        flash("Login failed due to a database error. Please try again.", "error")
        return redirect(url_for("auth.login_page"))

    login_user(user, remember=True)
    logger.info("GitHub OAuth login: user=%s created=%s", user.email, created)
    return redirect(url_for("dashboard.dashboard_page"))


