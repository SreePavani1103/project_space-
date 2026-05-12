
import pytest
from unittest.mock import patch, MagicMock
from backend.services.leetcode_service import extract_username, fetch_leetcode_profile, analyze_leetcode

def test_extract_username_leetcode():
    assert extract_username("https://leetcode.com/jack") == "jack"
    assert extract_username("https://leetcode.com/u/jack/") == "jack"
    assert extract_username("jack") == "jack"

@patch("requests.post")
def test_fetch_leetcode_profile_success(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "data": {
            "matchedUser": {
                "username": "jack",
                "profile": {"realName": "Jack Doe", "ranking": 5000},
                "submitStatsGlobal": {
                    "acSubmissionNum": [
                        {"difficulty": "All", "count": 100},
                        {"difficulty": "Easy", "count": 50},
                        {"difficulty": "Medium", "count": 40},
                        {"difficulty": "Hard", "count": 10}
                    ]
                },
                "tagProblemCounts": {
                    "fundamental": [{"tagName": "Array", "tagSlug": "array", "problemsSolved": 20}],
                    "intermediate": [],
                    "advanced": []
                }
            },
            "userContestRanking": {"rating": 1500, "attendedContestsCount": 5}
        }
    }
    
    result = fetch_leetcode_profile("jack")
    assert result["username"] == "jack"
    assert result["total_solved"] == 100
    assert result["easy_solved"] == 50
    assert result["contest_rating"] == 1500

def test_analyze_leetcode_logic():
    # Test Beginner level
    profile = {
        "total_solved": 10, "easy_solved": 10, "medium_solved": 0, "hard_solved": 0,
        "topics": {"Array": {"solved": 5, "level": "fundamental"}}
    }
    with patch("backend.services.leetcode_service.fetch_leetcode_profile", return_value=profile):
        result = analyze_leetcode("user")
        assert result["dsa_readiness_level"] == "Beginner"
        
    # Test Advanced level
    profile = {
        "total_solved": 600, "easy_solved": 200, "medium_solved": 300, "hard_solved": 100,
        "topics": {"Graph": {"solved": 50, "level": "advanced"}}
    }
    with patch("backend.services.leetcode_service.fetch_leetcode_profile", return_value=profile):
        result = analyze_leetcode("user")
        assert result["dsa_readiness_level"] == "Advanced"
        assert "Graph" in result["strong_topics"]
