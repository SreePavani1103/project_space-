
import pytest
import json
from unittest.mock import patch, MagicMock
from backend.services.ai_service import generate_text, generate_json, generate_resume_analysis

@pytest.fixture
def mock_genai_model():
    with patch("backend.services.ai_service._get_model") as mock_get:
        mock_model = MagicMock()
        mock_get.return_value = mock_model
        yield mock_model

def test_generate_text_success(mock_genai_model):
    mock_response = MagicMock()
    mock_response.text = "Hello from AI"
    mock_genai_model.generate_content.return_value = mock_response
    
    result = generate_text("Hi")
    assert result == "Hello from AI"

def test_generate_json_success(mock_genai_model):
    mock_response = MagicMock()
    mock_response.text = '{"key": "value"}'
    mock_genai_model.generate_content.return_value = mock_response
    
    result = generate_json("Give me JSON")
    assert result == {"key": "value"}

def test_generate_json_with_markdown_fences(mock_genai_model):
    mock_response = MagicMock()
    mock_response.text = '```json\n{"key": "value"}\n```'
    mock_genai_model.generate_content.return_value = mock_response
    
    result = generate_json("Give me JSON")
    assert result == {"key": "value"}

@patch("backend.services.ai_service.generate_json")
def test_generate_resume_analysis(mock_gen_json):
    mock_gen_json.return_value = {"ats_score": 85}
    result = generate_resume_analysis("Some resume text", "Software Engineer")
    assert result["ats_score"] == 85
    mock_gen_json.assert_called_once()
