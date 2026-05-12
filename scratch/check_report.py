import sys, json
sys.path.insert(0, '.')
from backend import create_app
from backend.models.report import Report

app = create_app()
with app.app_context():
    report = Report.query.order_by(Report.id.desc()).first()
    if not report:
        print('NO REPORTS FOUND')
    else:
        data = report.get_data()
        print("Report ID:", report.id)
        print("Target Role:", report.target_role)
        print("ATS Score:", report.ats_score)
        print("Hiring Readiness:", report.hiring_readiness)
        print("DSA Level:", report.dsa_level)
        print("GitHub Score:", report.github_score)
        print()

        ai = data.get('ai_report', {})
        print("=== AI REPORT ===")
        print("  Error:", ai.get("error", "None"))
        print("  Hiring Readiness %:", ai.get("hiring_readiness_percentage", "MISSING"))
        print("  Strong Skills:", len(ai.get("strong_skills", [])), "items")
        print("  Weak Skills:", len(ai.get("weak_skills", [])), "items")
        print("  Missing Skills:", len(ai.get("missing_skills", [])), "items")
        print("  Roadmap Phases:", len(ai.get("improvement_roadmap", [])), "phases")
        print("  Recommended Projects:", len(ai.get("recommended_projects", [])), "items")
        print("  Coding Questions:", len(ai.get("coding_questions_to_practice", [])), "topics")
        print("  Overall Assessment:", bool(ai.get("overall_assessment")))
        print()

        res = data.get('resources', {})
        print("=== RESOURCES ===")
        print("  Error:", res.get("error", "None"))
        print("  YouTube Playlists:", len(res.get("youtube_playlists", [])), "items")
        print("  GitHub Repos:", len(res.get("github_repositories", [])), "items")
        print("  Articles & Docs:", len(res.get("articles_and_docs", [])), "items")
        print("  Courses:", len(res.get("courses", [])), "items")
        print("  DSA Sheets:", len(res.get("dsa_sheets", [])), "items")
        print()

        gh = data.get('github_analysis', {})
        print("=== GITHUB ANALYSIS ===")
        print("  Error:", gh.get("error", "None"))
        print("  Total Repos:", gh.get("total_repos", "MISSING"))
        print("  Languages:", list(gh.get("languages", {}).keys())[:5])
        print()

        lc = data.get('leetcode_analysis', {})
        print("=== LEETCODE ANALYSIS ===")
        print("  Error:", lc.get("error", "None"))
        print("  Total Solved:", lc.get("total_solved", "MISSING"))
        print("  DSA Level:", lc.get("dsa_readiness_level", "MISSING"))
        print()

        print("=== ERRORS IN REPORT ===")
        for e in data.get('errors', []):
            print(" -", e)
