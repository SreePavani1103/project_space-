
import pytest
import io
import os
from unittest.mock import patch, MagicMock
from backend.models.user import User
from backend.models.report import Report

@pytest.fixture
def auth_client(client, db):
    user = User(email="tester@example.com", name="Tester")
    user.set_password("password")
    db.session.add(user)
    db.session.commit()
    client.post("/auth/api/login", json={"email": "tester@example.com", "password": "password"})
    return client

def test_analyze_api_unauthorized(client):
    response = client.post("/api/analyze", data={"target_role": "Backend Engineer"})
    # Flask-Login redirects to login page (302) by default
    assert response.status_code == 302

def test_analyze_api_missing_target_role(auth_client):
    response = auth_client.post("/api/analyze", data={"github_url": "octocat"})
    assert response.status_code == 400
    assert "Target role is required" in response.json["error"]

@patch("backend.services.rag_service.query_role")
@patch("backend.services.ai_service.generate_json")
@patch("backend.services.resume_service.extract_text")
@patch("backend.services.github_service.analyze_github")
def test_analyze_api_success(mock_github, mock_resume_text, mock_ai, mock_rag, auth_client, db, app):
    # Setup mocks
    mock_rag.return_value = {
        "found": True, 
        "context": "Backend role context", 
        "role_data": {"role": "Backend Engineer", "required_skills": ["Python"]}
    }
    mock_ai.return_value = {
        "ats_score": 85, 
        "hiring_readiness_percentage": 90, 
        "weak_skills": [], 
        "missing_skills": [],
        "summary": "Great candidate"
    }
    mock_resume_text.return_value = "Python Developer resume content"
    mock_github.return_value = {
        "profile": {"login": "testuser"},
        "languages": {"Python": 100},
        "frameworks": ["Flask"],
        "total_repos": 5
    }
    
    # Prepare multipart data
    data = {
        "target_role": "Backend Engineer",
        "github_url": "https://github.com/testuser",
        "resume": (io.BytesIO(b"Fake PDF Content"), "resume.pdf")
    }
    
    # Create upload folder if missing (though conftest uses in-memory DB, file system is real)
    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        os.makedirs(app.config["UPLOAD_FOLDER"])

    response = auth_client.post(
        "/api/analyze",
        data=data,
        content_type="multipart/form-data"
    )
    
    assert response.status_code == 200
    assert "report_id" in response.json
    
    # Verify report in DB
    report = Report.query.get(response.json["report_id"])
    assert report is not None
    assert report.target_role == "Backend Engineer"
