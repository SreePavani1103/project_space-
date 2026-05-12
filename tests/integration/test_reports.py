
import pytest
from backend.models.user import User
from backend.models.report import Report

@pytest.fixture
def auth_client_with_report(client, db):
    user = User(email="report_user@example.com")
    user.set_password("pass")
    db.session.add(user)
    db.session.commit()
    client.post("/auth/api/login", json={"email": "report_user@example.com", "password": "pass"})
    
    report = Report(
        user_id=user.id,
        target_role="Software Engineer",
        ats_score=80,
        hiring_readiness=70
    )
    report.set_data({"summary": {"role": "Software Engineer"}})
    db.session.add(report)
    db.session.commit()
    return client, report

def test_list_reports(auth_client_with_report):
    client, report = auth_client_with_report
    response = client.get("/api/reports")
    assert response.status_code == 200
    assert len(response.json["reports"]) == 1
    assert response.json["reports"][0]["target_role"] == "Software Engineer"

def test_get_report_detail(auth_client_with_report):
    client, report = auth_client_with_report
    response = client.get(f"/api/report/{report.id}")
    assert response.status_code == 200
    assert response.json["report"]["target_role"] == "Software Engineer"

def test_get_report_not_found(client, db):
    # Login but no report
    user = User(email="no_report@example.com")
    user.set_password("pass")
    db.session.add(user)
    db.session.commit()
    client.post("/auth/api/login", json={"email": "no_report@example.com", "password": "pass"})
    
    response = client.get("/api/report/999")
    assert response.status_code == 404

def test_delete_report(auth_client_with_report):
    client, report = auth_client_with_report
    response = client.delete(f"/api/report/{report.id}")
    assert response.status_code == 200
    assert response.json["success"] is True
    
    # Verify deleted
    assert Report.query.get(report.id) is None
