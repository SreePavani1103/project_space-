"""
Background tasks for Skill Synth AI (Redis + RQ).

Architecture:
- Phase 1 (parallel): Resume parse + GitHub fetch + LeetCode fetch + RAG lookup
- Phase 2 (parallel): AI analysis of resume, GitHub, LeetCode simultaneously
- Phase 3 (parallel): Skill gap synthesis + Resource recommendations simultaneously
- Phase 4 (sequential): DB write (cannot be parallelised)

Key fix: run_with_context() pushes a fresh Flask app context into each worker
thread so that current_app, db, and Gemini API key are all accessible.
"""
import os
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.extensions import db
from backend.models.user import User
from backend.models.report import Report
from backend.services.github_service import analyze_github
from backend.services.leetcode_service import analyze_leetcode
from backend.services.resume_service import analyze_resume
from backend.services.rag_service import query_role
from backend.services.skill_gap_service import compute_skill_gap
from backend.services.ai_service import (
    generate_resume_analysis, generate_github_analysis,
    generate_leetcode_analysis, generate_skill_gap_report,
    generate_resource_recommendations,
)
from backend.services.report_service import generate_full_report, export_report_pdf

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Standalone sub-tasks (kept for backwards compatibility)
# ─────────────────────────────────────────────────────────────

def fetch_github_stats(user_id, github_url):
    from backend import create_app
    app = create_app()
    with app.app_context():
        try:
            result = analyze_github(github_url)
            user = db.session.get(User, user_id)
            if user:
                user.last_synced_at = datetime.utcnow()
                db.session.commit()
            return result
        except Exception as e:
            logger.error("GitHub task failed for user %s: %s", user_id, e)
            raise


def fetch_leetcode_stats(user_id, leetcode_username):
    from backend import create_app
    app = create_app()
    with app.app_context():
        try:
            result = analyze_leetcode(leetcode_username)
            user = db.session.get(User, user_id)
            if user:
                user.last_synced_at = datetime.utcnow()
                db.session.commit()
            return result
        except Exception as e:
            logger.error("LeetCode task failed for user %s: %s", user_id, e)
            raise


# ─────────────────────────────────────────────────────────────
# Main orchestration task
# ─────────────────────────────────────────────────────────────

def generate_analysis_task(user_id, target_role, github_url, leetcode_username, resume_path):
    """
    Fully parallelised analysis pipeline.

    Execution timeline (approximate):
    t=0   ─── Phase 1 starts: resume / github / leetcode / rag in parallel
    t=10  ─── Phase 1 done (was 40s sequential)
    t=10  ─── Phase 2 starts: 3 Gemini calls in parallel
    t=25  ─── Phase 2 done (was 45s sequential)
    t=25  ─── Phase 3 starts: skill-gap + resources Gemini calls in parallel
    t=35  ─── Phase 3 done (was 30s sequential)
    t=35  ─── DB write, job done
    Total: ~35s vs ~115s sequential
    """
    from backend import create_app
    from rq import get_current_job

    app = create_app()
    job = get_current_job()

    def set_progress(msg: str):
        """Write progress to RQ job metadata for frontend polling."""
        if job:
            job.meta["progress"] = msg
            job.save_meta()
        logger.info("[TASK] %s", msg)

    def run_in_context(func, *args, **kwargs):
        """
        Push a fresh Flask app context into a worker thread.
        Required because ThreadPoolExecutor threads don't inherit the parent's context.
        """
        with app.app_context():
            return func(*args, **kwargs)

    with app.app_context():
        results = {"target_role": target_role, "errors": []}

        try:
            # ── Phase 1: Parallel data fetching ───────────────────────
            set_progress("Fetching raw data...")

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {}
                if resume_path and os.path.exists(resume_path):
                    futures["resume"] = executor.submit(run_in_context, analyze_resume, resume_path, target_role)
                if github_url:
                    futures["github"] = executor.submit(run_in_context, analyze_github, github_url)
                if leetcode_username:
                    futures["leetcode"] = executor.submit(run_in_context, analyze_leetcode, leetcode_username)
                futures["rag"] = executor.submit(run_in_context, query_role, target_role)

                # Collect all results (non-blocking wait — all run concurrently)
                resolved = {}
                for key, future in futures.items():
                    try:
                        resolved[key] = future.result(timeout=30)
                    except Exception as e:
                        logger.error("Phase 1 [%s] failed: %s", key, e)
                        resolved[key] = {}

            # ── Note: Resume file cleanup is now handled by the user/admin (Persistent Storage) ──
            # if resume_path:
            #     try:
            #         os.remove(resume_path)
            #     except OSError:
            #         pass

            # ── Unpack Phase 1 results ────────────────────────────────
            resume_analysis = resolved.get("resume", {}) or {}
            resume_text = resume_analysis.pop("text", "")
            if resume_analysis:
                results["resume_analysis"] = resume_analysis

            github_data = resolved.get("github", {}) or {}
            if github_data:
                results["github_analysis"] = github_data
                if "error" in github_data:
                    results["errors"].append(f"GitHub: {github_data['error']}")

            leetcode_data = resolved.get("leetcode", {}) or {}
            if leetcode_data:
                results["leetcode_analysis"] = leetcode_data
                if "error" in leetcode_data:
                    results["errors"].append(f"LeetCode: {leetcode_data['error']}")

            rag_result = resolved.get("rag", {}) or {}
            role_context = rag_result.get("context", "")
            role_data = rag_result.get("role_data") or {}
            results["rag_match"] = {
                "found": rag_result.get("found", False),
                "matched_role": rag_result.get("matched_role", ""),
            }

            # ── Skill gap (pure Python, fast) ─────────────────────────
            set_progress("Analyzing skills...")
            user_skills = list(resume_analysis.get("skills_detected", []))
            if github_data and "languages" in github_data:
                user_skills += list(github_data["languages"].keys())
            if github_data and "frameworks" in github_data:
                user_skills += list(github_data.get("frameworks", []))
            user_skills = list(set(s.lower() for s in user_skills))

            skill_gap = {}
            if role_data:
                skill_gap = compute_skill_gap(user_skills, role_data)
                results["skill_gap"] = skill_gap

            # ── Phase 2: Parallel Gemini AI analysis ──────────────────
            set_progress("Generating AI insights...")

            with ThreadPoolExecutor(max_workers=3) as executor:
                ai_futures = {}
                if resume_text:
                    ai_futures["ai_resume"] = executor.submit(
                        run_in_context, generate_resume_analysis, resume_text, target_role, role_context
                    )
                if github_data and "error" not in github_data:
                    ai_futures["ai_github"] = executor.submit(
                        run_in_context, generate_github_analysis, github_data, target_role, role_context
                    )
                if leetcode_data and "error" not in leetcode_data:
                    ai_futures["ai_leetcode"] = executor.submit(
                        run_in_context, generate_leetcode_analysis, leetcode_data, target_role
                    )

                ai_resolved = {}
                for key, future in ai_futures.items():
                    try:
                        ai_resolved[key] = future.result(timeout=90)
                    except Exception as e:
                        logger.error("Phase 2 [%s] failed: %s", key, e)
                        ai_resolved[key] = {}

            ai_resume = ai_resolved.get("ai_resume", {})
            ai_github = ai_resolved.get("ai_github", {})
            ai_leetcode = ai_resolved.get("ai_leetcode", {})

            if ai_resume:
                results["ai_resume_analysis"] = ai_resume
                if "error" in ai_resume:
                    results["errors"].append(f"AI Resume: {ai_resume['error']}")
            if ai_github:
                results["ai_github_analysis"] = ai_github
            if ai_leetcode:
                results["ai_leetcode_analysis"] = ai_leetcode

            # ── Phase 3: Parallel synthesis ───────────────────────────
            set_progress("Synthesizing final report...")

            with ThreadPoolExecutor(max_workers=2) as executor:
                f_report = executor.submit(
                    run_in_context,
                    generate_skill_gap_report,
                    user_skills, role_data, ai_resume, ai_github, ai_leetcode, target_role, role_context,
                )
                f_resources = executor.submit(
                    run_in_context,
                    generate_resource_recommendations,
                    user_skills, role_data, target_role,
                )

                ai_report = {}
                resources = {}
                try:
                    ai_report = f_report.result(timeout=120)
                except Exception as e:
                    logger.error("Skill gap report failed: %s", e)
                    ai_report = {
                        "overall_assessment": f"AI analysis unavailable: {e}",
                        "strong_skills": [], "missing_skills": [],
                    }
                try:
                    resources = f_resources.result(timeout=120)
                except Exception as e:
                    logger.error("Resource recommendations failed: %s", e)
                    resources = {}

            results["ai_report"] = ai_report
            results["resources"] = resources

            # ── Phase 4: DB write (sequential — must be in main context) ──
            set_progress("Saving report...")

            resume_combined = {**results.get("resume_analysis", {}), **results.get("ai_resume_analysis", {})}
            github_combined = {**results.get("github_analysis", {}), **results.get("ai_github_analysis", {})}
            leetcode_combined = {**results.get("leetcode_analysis", {}), **results.get("ai_leetcode_analysis", {})}

            full_report_data = generate_full_report(
                resume_combined, github_combined, leetcode_combined,
                skill_gap, ai_report, resources, target_role,
            )

            report = Report(
                user_id=user_id,
                target_role=target_role,
                ats_score=full_report_data["summary"]["ats_score"],
                hiring_readiness=full_report_data["summary"]["hiring_readiness"],
                dsa_level=full_report_data["summary"]["dsa_level"],
                github_score=full_report_data["summary"]["github_score"],
            )
            report.set_data(full_report_data)
            db.session.add(report)

            user = db.session.get(User, user_id)
            if user:
                user.last_synced_at = datetime.utcnow()

            db.session.commit()
            set_progress("Done!")
            return {"report_id": report.id, "success": True}

        except Exception as e:
            logger.error("Analysis task failed: %s", e)
            return {"error": str(e), "success": False}
