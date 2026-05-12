import sys
sys.path.insert(0, '.')

from backend import create_app
app = create_app()

errors = []
with app.app_context():
    # --- Import checks ---
    try:
        from backend.services.report_service import generate_full_report, _safe_text
        from backend.services.rag_service import _get_collection, _init_lock
        from backend.services.skill_gap_service import compute_skill_gap
        print("OK: All imports")
    except Exception as e:
        errors.append(f"FAIL import: {e}")

    # --- _safe_text ---
    try:
        result = _safe_text("Hello <World> & co")
        assert result == "Hello &lt;World&gt; &amp; co", f"Got: {result}"
        print("OK: _safe_text escaping")
    except Exception as e:
        errors.append(f"FAIL _safe_text: {e}")

    # --- skill gap int cast ---
    try:
        gap = compute_skill_gap(["python", "flask"], {"required_skills": ["Python", "Flask", "Docker"]})
        assert isinstance(gap["hiring_readiness"], int), f"Got type: {type(gap['hiring_readiness'])}"
        print("OK: hiring_readiness is int, value =", gap["hiring_readiness"])
    except Exception as e:
        errors.append(f"FAIL skill_gap: {e}")

    # --- PDF export with NEW roadmap dict format ---
    try:
        from backend.services.report_service import export_report_pdf
        report_data = {
            "target_role": "Backend Developer",
            "generated_at": "2026-01-01T00:00:00",
            "summary": {"ats_score": 80, "hiring_readiness": 70, "dsa_level": "Intermediate", "github_score": 60},
            "ai_report": {
                "overall_assessment": "Good candidate with strong Python skills.",
                "strong_skills": [{"skill": "Python", "evidence": "Used in 5+ projects"}],
                "missing_skills": [{"skill": "Docker", "importance": "critical", "description": "Needed for prod"}],
                "improvement_roadmap": {
                    "day_30": {"goal": "Learn Docker", "tasks": ["Install Docker", "Build image"], "skills_to_cover": ["Docker"]},
                    "day_60": {"goal": "Build APIs", "tasks": ["FastAPI project"], "skills_to_cover": ["FastAPI"]},
                    "day_90": {"goal": "Cloud deploy", "tasks": ["AWS EC2"], "skills_to_cover": ["AWS"]},
                },
            },
        }
        pdf = export_report_pdf(report_data)
        assert len(pdf) > 1000, "PDF too small"
        print("OK: PDF export with new roadmap dict format, size =", len(pdf), "bytes")
    except Exception as e:
        errors.append(f"FAIL PDF export: {e}")

    # --- PDF export with OLD roadmap list format (backwards compat) ---
    try:
        report_data2 = dict(report_data)
        report_data2["ai_report"] = dict(report_data["ai_report"])
        report_data2["ai_report"]["improvement_roadmap"] = [
            {"phase": 1, "title": "Foundations", "duration": "2 weeks", "tasks": ["Learn basics"]},
        ]
        pdf2 = export_report_pdf(report_data2)
        assert len(pdf2) > 1000, "PDF2 too small"
        print("OK: PDF export with old roadmap list format, size =", len(pdf2), "bytes")
    except Exception as e:
        errors.append(f"FAIL PDF legacy roadmap: {e}")

print()
if errors:
    print("=== FAILURES ===")
    for e in errors:
        print(" -", e)
else:
    print("=== ALL CHECKS PASSED ===")
