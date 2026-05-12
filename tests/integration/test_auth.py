
import pytest
from backend.models.user import User

def test_api_register_success(client, db):
    response = client.post("/auth/api/register", json={
        "name": "New User",
        "email": "new@example.com",
        "password": "password123"
    })
    assert response.status_code == 201
    assert response.json["success"] is True
    
    # Verify in DB
    user = User.query.filter_by(email="new@example.com").first()
    assert user is not None
    assert user.name == "New User"

def test_api_register_duplicate_email(client, db):
    # First registration
    client.post("/auth/api/register", json={
        "email": "dup@example.com",
        "password": "password123"
    })
    # Second registration
    response = client.post("/auth/api/register", json={
        "email": "dup@example.com",
        "password": "password123"
    })
    assert response.status_code == 409
    assert "already registered" in response.json["error"]

def test_api_login_success(client, db):
    # Setup user
    user = User(email="login@example.com", name="Login User")
    user.set_password("correct_password")
    db.session.add(user)
    db.session.commit()
    
    response = client.post("/auth/api/login", json={
        "email": "login@example.com",
        "password": "correct_password"
    })
    assert response.status_code == 200
    assert response.json["success"] is True
    assert response.json["user"]["email"] == "login@example.com"

def test_api_login_fail(client, db):
    response = client.post("/auth/api/login", json={
        "email": "wrong@example.com",
        "password": "wrong"
    })
    assert response.status_code == 401

def test_api_me_unauthorized(client):
    response = client.get("/auth/api/me")
    assert response.json["authenticated"] is False

def test_api_logout(client, db):
    # Login first
    user = User(email="logout@example.com")
    user.set_password("pass")
    db.session.add(user)
    db.session.commit()
    client.post("/auth/api/login", json={"email": "logout@example.com", "password": "pass"})
    
    response = client.post("/auth/api/logout")
    assert response.status_code == 200
    
    # Verify logged out
    me_resp = client.get("/auth/api/me")
    assert me_resp.json["authenticated"] is False
