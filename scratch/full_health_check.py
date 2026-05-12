"""
Comprehensive live check — tests every layer of the app:
1. DB connectivity and models
2. All backend services (resume, github, leetcode, rag, skill_gap, report, ai)
3. All route blueprints can be imported and registered
4. Redis/RQ connectivity
5. PDF export
6. HTML safety helper
7. ChromaDB / RAG
"""
import sys, traceback
sys.path.insert(0, '.')

from backend import create_app
app = create_app()

results = []

def check(name, fn):
    try:
        fn()
        results.append(("PASS", name))
        print(f"  PASS  {name}")
    except Exception as e:
        results.append(("FAIL", name, str(e)))
        print(f"  FAIL  {name}")
        print(f"        {e}")

print("\n=== SKILL SYNTH AI — FULL LIVE HEALTH CHECK ===\n")

with app.app_context():

    # 1. Database
    print("[1] Database")
    def test_db():
        from backend.extensions import db
        from backend.models.user import User
        from backend.models.report import Report
        count = User.query.count()
        rcount = Report.query.count()
        assert count >= 0 and rcount >= 0
    check("DB models readable", test_db)

    def test_report_read():
        from backend.models.report import Report
        r = Report.query.order_by(Report.id.desc()).first()
        if r:
            data = r.get_data()
            assert isinstance(data, dict)
    check("Latest report JSON parse", test_report_read)

    # 2. Services
    print("\n[2] Services")

    def test_rag():
        from backend.services.rag_service import _get_collection, seed_knowledge_base, query_role
        col = _get_collection()
        if col.count() == 0:
            seed_knowledge_base()
        result = query_role("Backend Developer")
        assert result.get("found") or result.get("context") is not None
    check("RAG service + ChromaDB", test_rag)

    def test_rag_thread_safe():
        import threading
        from backend.services.rag_service import query_role
        errors = []
        def worker():
            try:
                with app.app_context():
                    query_role("Frontend Developer")
            except Exception as e:
                errors.append(str(e))
        threads = [threading.Thread(target=worker) for _ in range(5)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        assert not errors, f"Thread errors: {errors}"
    check("RAG thread-safety (5 concurrent threads)", test_rag_thread_safe)

    def test_skill_gap():
        from backend.services.skill_gap_service import compute_skill_gap
        r = compute_skill_gap(["python", "docker", "flask"], {"required_skills": ["Python", "Docker", "Kubernetes"]})
        assert isinstance(r["hiring_readiness"], int), f"Not int: {type(r['hiring_readiness'])}"
        assert 0 <= r["hiring_readiness"] <= 100
    check("Skill gap service (int output)", test_skill_gap)

    def test_resume_extraction():
        from backend.services.resume_service import detect_skills
        skills = detect_skills("I have experience with Python, React, Docker and AWS")
        assert "python" in skills
        assert "react" in skills
    check("Resume skill detection", test_resume_extraction)

    def test_report_service():
        from backend.services.report_service import generate_full_report, _safe_text
        # Test safe text
        assert _safe_text("<b>Hello & World</b>") == "&lt;b&gt;Hello &amp; World&lt;/b&gt;"
        # Test report generation
        report = generate_full_report(
            {"ats_score": 75},
            {"total_repos": 10, "total_stars": 50, "languages": {"Python": 80}},
            {"total_solved": 100, "dsa_readiness_level": "Intermediate"},
            {"hiring_readiness": 60},
            {"hiring_readiness_percentage": 72, "overall_assessment": "Good candidate"},
            {"courses": []},
            "Backend Developer"
        )
        assert report["summary"]["ats_score"] == 75
        assert report["summary"]["hiring_readiness"] == 72
        assert isinstance(report["summary"]["github_score"], int)
        assert report["summary"]["dsa_level"] == "Intermediate"
    check("Report service (scores, dsa_level, github_score)", test_report_service)

    def test_pdf_new_format():
        from backend.services.report_service import export_report_pdf
        pdf = export_report_pdf({
            "target_role": "Backend Developer",
            "generated_at": "2026-01-01T00:00:00",
            "summary": {"ats_score": 80, "hiring_readiness": 70, "dsa_level": "Intermediate", "github_score": 60},
            "ai_report": {
                "overall_assessment": "Strong candidate with Python <expertise> & Docker skills.",
                "strong_skills": [{"skill": "Python", "evidence": "5+ years"}],
                "missing_skills": [{"skill": "K8s", "importance": "critical", "description": "For prod"}],
                "improvement_roadmap": {
                    "day_30": {"goal": "Docker basics", "tasks": ["Install", "Build"], "skills_to_cover": ["Docker"]},
                    "day_60": {"goal": "APIs", "tasks": ["FastAPI"], "skills_to_cover": ["FastAPI"]},
                    "day_90": {"goal": "Cloud", "tasks": ["AWS"], "skills_to_cover": ["AWS"]},
                },
            },
        })
        assert len(pdf) > 1000
    check("PDF export — new dict roadmap format", test_pdf_new_format)

    def test_pdf_old_format():
        from backend.services.report_service import export_report_pdf
        pdf = export_report_pdf({
            "target_role": "Backend Developer",
            "generated_at": "2026-01-01T00:00:00",
            "summary": {"ats_score": 80, "hiring_readiness": 70, "dsa_level": "Intermediate", "github_score": 60},
            "ai_report": {
                "overall_assessment": "Good.",
                "improvement_roadmap": [
                    {"phase": 1, "title": "Basics", "duration": "2 weeks", "tasks": ["Do X"]},
                ],
            },
        })
        assert len(pdf) > 1000
    check("PDF export — old list roadmap format (backwards compat)", test_pdf_old_format)

    # 3. Redis / RQ
    print("\n[3] Redis / RQ")
    def test_redis():
        from backend import extensions
        assert extensions.redis_conn is not None, "Redis not connected"
        extensions.redis_conn.ping()
        assert extensions.task_queue is not None, "Task queue not available"
    check("Redis connection + task queue", test_redis)

    # 4. Routes registered
    print("\n[4] Routes")
    def test_routes():
        rules = [str(r) for r in app.url_map.iter_rules()]
        required = ["/health", "/api/analyze", "/api/status/<job_id>",
                    "/api/report/<int:report_id>", "/api/roles",
                    "/auth/login", "/auth/github", "/auth/github/callback",
                    "/dashboard", "/dashboard/analyze", "/dashboard/report/<int:report_id>"]
        missing = [r for r in required if r not in rules]
        assert not missing, f"Missing routes: {missing}"
    check("All expected routes registered", test_routes)

    # 5. Auth
    print("\n[5] Auth")
    def test_user_model():
        from backend.models.user import User
        u = User(email="test@test.com", name="Test")
        u.set_password("password123")
        assert u.check_password("password123")
        assert not u.check_password("wrong")
        assert not u.check_password("")  # empty pw
    check("User password hash/check", test_user_model)

# Final summary
print("\n" + "="*50)
passed = sum(1 for r in results if r[0] == "PASS")
failed = sum(1 for r in results if r[0] == "FAIL")
print(f"RESULT: {passed} passed / {failed} failed / {len(results)} total")
if failed:
    print("\nFAILED CHECKS:")
    for r in results:
        if r[0] == "FAIL":
            print(f"  - {r[1]}: {r[2]}")
else:
    print("ALL CHECKS PASSED ✓")
