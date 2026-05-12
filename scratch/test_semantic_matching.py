import sys
import os
sys.path.insert(0, os.getcwd())

from backend.services.skill_gap_service import semantic_skill_match, compute_skill_gap

def test_semantic_matching():
    print("--- Testing Semantic Matching ---")
    
    user_skills = ["React.js", "Python 3", "Docker Containers", "SQL Databases"]
    required_skills = ["React", "Python", "Docker", "PostgreSQL", "Kubernetes"]
    
    print(f"User Skills: {user_skills}")
    print(f"Required Skills: {required_skills}")
    
    strong, missing, extra = semantic_skill_match(user_skills, required_skills)
    
    print(f"\nStrong Matches: {strong}")
    print(f"Missing Skills: {missing}")
    print(f"Extra Skills: {extra}")
    
    # Expected: 
    # Strong: React, Python, Docker (semantic matches)
    # Missing: PostgreSQL, Kubernetes (PostgreSQL might be close to SQL, but Kubernetes is different)
    
    assert "React" in strong
    assert "Python" in strong
    assert "Docker" in strong
    assert "Kubernetes" in missing

    print("\n--- Testing compute_skill_gap ---")
    role_data = {
        "role": "Backend Developer",
        "required_skills": required_skills
    }
    result = compute_skill_gap(user_skills, role_data)
    print(f"Coverage: {result['coverage_percentage']}%")
    print(f"Readiness: {result['hiring_readiness']}")
    
    print("\nSUCCESS: Semantic matching verified.")

if __name__ == "__main__":
    try:
        test_semantic_matching()
    except Exception as e:
        print(f"\nFAILED: {e}")
        sys.exit(1)
