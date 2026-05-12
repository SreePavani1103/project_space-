
import pytest
from unittest.mock import patch, MagicMock
from backend.services.resume_service import detect_skills, detect_sections, basic_ats_check, extract_text

def test_detect_skills():
    text = "I am a developer with experience in Python, Flask, and PostgreSQL."
    skills = detect_skills(text)
    assert "python" in skills
    assert "flask" in skills
    assert "postgresql" in skills
    assert "java" not in skills

def test_detect_sections():
    text = "SUMMARY: I am a dev. EXPERIENCE: Google. EDUCATION: Stanford."
    sections = detect_sections(text)
    assert sections["summary"] is True
    assert sections["experience"] is True
    assert sections["education"] is True
    assert sections["projects"] is False

def test_basic_ats_check():
    text = "This is a long text to satisfy word count requirements. " * 50
    text += " CONTACT: test@example.com. EXPERIENCE: 2024. PROJECTS: AI."
    skills = ["python", "java", "sql", "git", "aws", "docker", "react", "node.js", "html", "css"]
    
    result = basic_ats_check(text, skills)
    assert result["ats_score"] >= 70
    assert result["word_count"] > 300
    assert result["sections"]["contact"] is True

@patch("backend.services.resume_service.extract_text_from_pdf")
def test_extract_text_pdf(mock_pdf):
    mock_pdf.return_value = "PDF Content"
    assert extract_text("test.pdf") == "PDF Content"
    mock_pdf.assert_called_once()
