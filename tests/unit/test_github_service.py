
import pytest
from unittest.mock import patch, MagicMock
from backend.services.github_service import extract_username, fetch_profile, analyze_github

def test_extract_username():
    assert extract_username("https://github.com/octocat") == "octocat"
    assert extract_username("https://github.com/octocat/") == "octocat"
    assert extract_username("octocat") == "octocat"

@patch("backend.services.github_service._get")
def test_fetch_profile_success(mock_get):
    mock_get.return_value = {
        "login": "octocat",
        "name": "The Octocat",
        "bio": "Hello World",
        "public_repos": 2,
        "followers": 10,
        "following": 5,
        "created_at": "2011-01-25T18:44:36Z",
        "avatar_url": "https://avatar.url",
        "html_url": "https://github.com/octocat"
    }
    profile = fetch_profile("octocat")
    assert profile["username"] == "octocat"
    assert profile["name"] == "The Octocat"

@patch("backend.services.github_service.fetch_profile")
@patch("backend.services.github_service.fetch_repos")
@patch("backend.services.github_service.fetch_languages")
def test_analyze_github_success(mock_langs, mock_repos, mock_profile):
    mock_profile.return_value = {"login": "octocat"}
    mock_repos.return_value = [
        {"name": "hello-world", "description": "A react app", "topics": ["react"], "updated_at": "2024-01-01"}
    ]
    mock_langs.return_value = {"JavaScript": 100.0}
    
    result = analyze_github("https://github.com/octocat")
    
    assert "profile" in result
    assert "React" in result["frameworks"]
    assert result["languages"]["JavaScript"] == 100.0
    assert result["total_repos"] == 1
