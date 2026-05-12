import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_api():
    session = requests.Session()
    
    print("--- Testing Public Endpoints ---")
    # 1. Get Roles
    resp = session.get(f"{BASE_URL}/api/roles")
    print(f"GET /api/roles: {resp.status_code}")
    print(f"Response: {resp.json() if resp.status_code == 200 else resp.text[:100]}")
    
    # 2. Check session (should be False)
    resp = session.get(f"{BASE_URL}/auth/api/me")
    print(f"GET /auth/api/me (unauthorized): {resp.status_code}")
    print(f"Response: {resp.json()}")

    print("\n--- Testing Authentication ---")
    # 3. Login
    login_data = {"email": "testuser@example.com", "password": "password123"}
    resp = session.post(f"{BASE_URL}/auth/api/login", json=login_data)
    print(f"POST /auth/api/login: {resp.status_code}")
    print(f"Response: {resp.json()}")

    # 4. Check session (should be True)
    resp = session.get(f"{BASE_URL}/auth/api/me")
    print(f"GET /auth/api/me (authorized): {resp.status_code}")
    print(f"Response: {resp.json()}")

    print("\n--- Testing Protected Endpoints ---")
    # 5. List Reports
    resp = session.get(f"{BASE_URL}/api/reports")
    print(f"GET /api/reports: {resp.status_code}")
    reports = resp.json().get("reports", [])
    print(f"Found {len(reports)} reports")
    if reports:
        report_id = reports[0]["id"]
        print(f"Testing /api/report/{report_id}")
        resp = session.get(f"{BASE_URL}/api/report/{report_id}")
        print(f"GET /api/report/{report_id}: {resp.status_code}")

    print("\n--- Testing Invalid Requests & Error Handling ---")
    # 6. Invalid Login
    resp = session.post(f"{BASE_URL}/auth/api/login", json={"email": "wrong@example.com", "password": "bad"})
    print(f"POST /auth/api/login (invalid): {resp.status_code}")
    print(f"Response: {resp.json()}")

    # 7. Analyze without target_role
    resp = session.post(f"{BASE_URL}/api/analyze", data={})
    print(f"POST /api/analyze (missing data): {resp.status_code}")
    print(f"Response: {resp.json()}")

    # 8. Get non-existent report
    resp = session.get(f"{BASE_URL}/api/report/999999")
    print(f"GET /api/report/999999: {resp.status_code}")
    print(f"Response: {resp.json()}")

if __name__ == "__main__":
    test_api()
