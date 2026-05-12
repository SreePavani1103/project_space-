import requests
import os
import shutil

BASE_URL = "http://127.0.0.1:5000"

def test_deletion_and_storage():
    session = requests.Session()
    
    # 1. Login
    login_data = {"email": "testuser@example.com", "password": "password123"}
    resp = session.post(f"{BASE_URL}/auth/api/login", json=login_data)
    user_id = resp.json()["user"]["id"]
    print(f"Logged in as user {user_id}")

    # 2. Upload resume
    resume_path = "sample_resume.pdf"
    if not os.path.exists(resume_path):
        with open(resume_path, "w") as f:
            f.write("dummy content")
            
    files = {"resume": open(resume_path, "rb")}
    data = {"target_role": "Backend Developer"}
    resp = session.post(f"{BASE_URL}/api/analyze", data=data, files=files)
    print(f"Upload response: {resp.status_code} - {resp.json()}")

    # 3. Verify persistent storage
    # We expect the file to be in uploads/resumes/<user_id>/
    storage_dir = os.path.join("uploads", "resumes", str(user_id))
    if os.path.exists(storage_dir) and os.listdir(storage_dir):
        print(f"SUCCESS: Resume stored persistently in {storage_dir}")
    else:
        print(f"FAILED: Resume not found in {storage_dir}")

    # 4. Delete account
    resp = session.delete(f"{BASE_URL}/api/user/me")
    print(f"Deletion response: {resp.status_code} - {resp.json()}")

    # 5. Verify cleanup
    if not os.path.exists(storage_dir):
        print(f"SUCCESS: Resume directory {storage_dir} deleted.")
    else:
        print(f"FAILED: Resume directory {storage_dir} still exists.")

    # 6. Verify login fails
    resp = session.post(f"{BASE_URL}/auth/api/login", json=login_data)
    if resp.status_code == 401:
        print("SUCCESS: User login fails after deletion.")
    else:
        print(f"FAILED: User still able to login? {resp.status_code}")

if __name__ == "__main__":
    test_deletion_and_storage()
