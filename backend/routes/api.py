"""
Analysis API routes — resume upload, GitHub/LeetCode analysis, full report generation.
"""
import os
import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from backend import extensions
from backend.extensions import limiter
from rq import Retry
from backend.tasks import generate_analysis_task, fetch_github_stats, fetch_leetcode_stats

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api")

ALLOWED_EXT = {"pdf", "docx"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


@api_bp.errorhandler(429)
def ratelimit_handler(e):
    """Return JSON 429 instead of HTML when rate limit is exceeded."""
    return jsonify({
        "error": "Rate limit exceeded. Please wait before running another analysis.",
        "retry_after": str(e.description)
    }), 429


@api_bp.route("/roles", methods=["GET"])
@limiter.limit("60 per hour")
def get_roles():
    from backend.services.rag_service import get_all_roles
    return jsonify({"roles": get_all_roles()})


@api_bp.route("/analyze", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
def run_analysis():
    """Enqueue full career analysis pipeline."""
    # 1. Collect inputs
    target_role = request.form.get("target_role", "").strip()
    github_url = request.form.get("github_url", "").strip()
    leetcode_username = request.form.get("leetcode_username", "").strip()
    resume_file = request.files.get("resume")

    if not target_role:
        return jsonify({"error": "Target role is required"}), 400

    if not resume_file and not github_url and not leetcode_username:
        return jsonify({"error": "Please provide at least one input."}), 400

    # 2. Handle resume file saving
    resume_path = None
    if resume_file and allowed_file(resume_file.filename):
        try:
            from backend.services.resume_storage_service import save_user_resume
            from backend.models.resume import Resume
            
            # Save file persistently
            resume_path = save_user_resume(current_user.id, resume_file)
            
            if resume_path:
                # Save metadata to DB
                new_resume = Resume(
                    user_id=current_user.id,
                    filename=os.path.basename(resume_path),
                    file_path=resume_path
                )
                extensions.db.session.add(new_resume)
                extensions.db.session.commit()
            else:
                # Fallback to current temporary processing if persistent fails
                filename = secure_filename(f"{current_user.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{resume_file.filename}")
                resume_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
                resume_file.save(resume_path)
                
        except Exception as e:
            logger.error("Failed to save resume: %s", e)
            return jsonify({"error": f"Failed to save resume: {str(e)}"}), 500
    elif resume_file:
        return jsonify({"error": "Invalid file type. Only PDF and DOCX are accepted."}), 400

    # 3. Enqueue the task
    try:
        # Guard: if Redis is unavailable, task_queue is None (set in __init__.py)
        if extensions.task_queue is None:
            return jsonify({"error": "Analysis service is temporarily unavailable. Please try again in a moment."}), 503
        job = extensions.task_queue.enqueue(
            generate_analysis_task,
            args=(current_user.id, target_role, github_url, leetcode_username, resume_path),
            job_timeout="10m",
            retry=Retry(max=3, interval=[10, 30, 60])
        )
        return jsonify({
            "status": "queued",
            "job_id": job.id,
            "message": "Analysis started in background"
        }), 202
    except Exception as e:
        logger.error("Failed to enqueue job: %s", e)
        return jsonify({"error": "Failed to start background analysis"}), 500



@api_bp.route("/status/<job_id>", methods=["GET"])
@login_required
def get_job_status(job_id):
    """Check the status of a background job."""
    from rq.job import Job
    
    try:
        job = Job.fetch(job_id, connection=extensions.redis_conn)
    except Exception:
        return jsonify({"status": "not_found", "error": "Job not found"}), 404

    job.refresh()
    status = str(job.get_status()).lower()
    # Normalize enum strings like 'JobStatus.finished' -> 'finished'
    if "." in status:
        status = status.split(".")[-1]

    result = job.result
    progress = job.meta.get("progress", "Initializing...")

    response = {
        "job_id": job_id,
        "status": status,
        "progress": progress
    }

    if status == "finished":
        if result and isinstance(result, dict) and result.get("success"):
            response["report_id"] = result.get("report_id")
        elif result and isinstance(result, dict) and result.get("error"):
            response["status"] = "failed"
            response["error"] = result.get("error")
    elif status == "failed":
        # BUG 4 FIX: read actual exception from job result, not a generic string
        error_msg = "Job failed during execution"
        try:
            latest = job.latest_result()
            if hasattr(latest, "exc_string") and latest.exc_string:
                # Extract last line of traceback (most descriptive, no file paths)
                lines = [l for l in latest.exc_string.strip().splitlines() if l.strip()]
                error_msg = lines[-1] if lines else error_msg
        except Exception:
            pass
        response["error"] = error_msg

    return jsonify(response)


@api_bp.route("/report/<int:report_id>", methods=["GET"])
@login_required
def get_report(report_id):
    from backend.models.report import Report
    report = Report.query.filter_by(id=report_id, user_id=current_user.id).first()
    if not report:
        return jsonify({"error": "Report not found"}), 404
    return jsonify({"report": report.to_dict(), "data": report.get_data()})


@api_bp.route("/report/<int:report_id>/pdf", methods=["GET"])
@login_required
def export_pdf(report_id):
    from backend.models.report import Report
    from backend.services.report_service import export_report_pdf
    import io

    report = Report.query.filter_by(id=report_id, user_id=current_user.id).first()
    if not report:
        return jsonify({"error": "Report not found"}), 404

    pdf_bytes = export_report_pdf(report.get_data())
    return send_file(io.BytesIO(pdf_bytes), mimetype="application/pdf", as_attachment=True, download_name=f"skill_synth_report_{report_id}.pdf")


@api_bp.route("/reports", methods=["GET"])
@login_required
def list_reports():
    from backend.models.report import Report
    reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).all()
    return jsonify({"reports": [r.to_dict() for r in reports]})


@api_bp.route("/report/<int:report_id>", methods=["DELETE"])
@login_required
def delete_report(report_id):
    from backend.models.report import Report
    report = Report.query.filter_by(id=report_id, user_id=current_user.id).first()
    if not report:
        return jsonify({"error": "Report not found"}), 404
    try:
        extensions.db.session.delete(report)
        extensions.db.session.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error("Failed to delete report %s: %s", report_id, e)
        extensions.db.session.rollback()
        return jsonify({"error": "Failed to delete report"}), 500
@api_bp.route("/user/me", methods=["DELETE"])
@login_required
def delete_account():
    """
    Deletes the current user's account and all associated data.
    """
    user_id = current_user.id
    try:
        from backend.models.user import User
        from backend.models.report import Report
        from backend.models.resume import Resume
        from backend.services.resume_storage_service import delete_user_files
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        # 1. Delete persistent files (resumes)
        delete_user_files(user_id)
        
        # 2. Delete DB records explicitly to ensure data is removed even without cascading relationships
        # Delete associated reports
        Report.query.filter_by(user_id=user_id).delete()
        # Delete resume metadata
        Resume.query.filter_by(user_id=user_id).delete()
        
        # 3. Delete user account
        extensions.db.session.delete(user)
        extensions.db.session.commit()
        
        # Log the user out after deletion
        from flask_login import logout_user
        logout_user()
        
        return jsonify({"message": "Account deleted successfully"}), 200
    except Exception as e:
        logger.error("Failed to delete account for user %s: %s", user_id, e)
        extensions.db.session.rollback()
        return jsonify({"error": "Failed to delete account"}), 500
