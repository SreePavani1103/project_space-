
from backend.services.skill_gap_service import compute_skill_gap

def test_compute_skill_gap_success():
    user_skills = ["Python", "Flask", "SQL"]
    role_data = {
        "role": "Backend Engineer",
        "required_skills": ["Python", "Django", "PostgreSQL"],
        "interview_topics": ["Database Design"],
        "hiring_expectations": {"experience": "2 years"}
    }
    result = compute_skill_gap(user_skills, role_data)
    
    assert result["role"] == "Backend Engineer"
    assert "python" in result["strong_skills"]
    assert "django" in result["missing_skills"]
    assert "flask" in result["extra_skills"]
    assert result["coverage_percentage"] == 33.3
    assert result["hiring_readiness"] > 0

def test_compute_skill_gap_no_role():
    result = compute_skill_gap(["Python"], {})
    assert "error" in result

def test_compute_skill_gap_full_coverage():
    user_skills = ["Python", "Django", "PostgreSQL"]
    role_data = {
        "required_skills": ["Python", "Django", "PostgreSQL"]
    }
    result = compute_skill_gap(user_skills, role_data)
    assert result["coverage_percentage"] == 100.0
    assert len(result["missing_skills"]) == 0
