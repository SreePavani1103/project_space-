import sys
import os
sys.path.insert(0, os.getcwd())
from backend import create_app
from backend.extensions import db
from backend.models.report import Report

app = create_app()
with app.app_context():
    r = Report.query.order_by(Report.id.desc()).first()
    if r:
        data = r.get_data()
        print(f"REPORT ID {r.id} DETAILS:")
        print("ERRORS:", data.get("errors", []))
        print("AI REPORT KEYS:", data.get("ai_report", {}).keys())
        print("GITHUB ANALYSIS KEYS:", data.get("github_analysis", {}).keys())
        print("LEETCODE ANALYSIS KEYS:", data.get("leetcode_analysis", {}).keys())
        if "error" in data.get("github_analysis", {}):
            print("GITHUB ERROR:", data["github_analysis"]["error"])
        if "error" in data.get("leetcode_analysis", {}):
            print("LEETCODE ERROR:", data["leetcode_analysis"]["error"])
