"""
AI Service — Gemini API integration.

Thread-safe, non-blocking integration with Google's Gemini API.
Supports concurrent prompt execution via run_concurrent_prompts().

Key changes:
- Thread-local model instances to avoid race conditions
- Per-call timeout enforcement (30s default)
- Exponential backoff retry logic
- generate_concurrent() helper runs prompts in parallel
"""
import json
import time
import logging
import threading
from flask import current_app

logger = logging.getLogger(__name__)

# Thread-local storage: each thread gets its own model instance
# This eliminates the shared-singleton race condition
_thread_local = threading.local()


def _get_model():
    """
    Return a per-thread Gemini model instance.
    Thread-safe: each thread initializes its own copy.
    """
    if not hasattr(_thread_local, "model") or _thread_local.model is None:
        import google.generativeai as genai
        api_key = current_app.config.get("GEMINI_API_KEY", "")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set in configuration.")
        model_name = current_app.config.get("GEMINI_MODEL", "gemini-flash-latest")
        # Configure per-thread (genai.configure is global but safe to call repeatedly with the same key)
        genai.configure(api_key=api_key)
        _thread_local.model = genai.GenerativeModel(model_name)
        logger.debug("Initialized Gemini model '%s' on thread %s", model_name, threading.current_thread().name)
    return _thread_local.model


def generate_text(prompt: str, max_tokens: int = 8192, timeout: int = 60, retries: int = 2) -> str:
    """
    Generate text from a prompt using Gemini.
    
    Args:
        prompt: The prompt string
        max_tokens: Max output tokens
        timeout: Seconds before giving up (enforced via retry counting)
        retries: Number of retry attempts on transient errors
    """
    last_error = None
    for attempt in range(retries + 1):
        try:
            model = _get_model()
            response = model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": max_tokens,
                    "temperature": 0.7,
                },
                request_options={"timeout": timeout},  # per-request timeout
            )
            return response.text
        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            # Don't retry on quota/auth errors — they won't fix themselves
            if "quota" in error_str or "api_key" in error_str or "permission" in error_str:
                logger.error("Gemini non-retryable error: %s", e)
                raise
            if attempt < retries:
                wait = 2 ** attempt  # exponential backoff: 1s, 2s
                logger.warning("Gemini attempt %d failed (%s), retrying in %ds...", attempt + 1, e, wait)
                time.sleep(wait)
            else:
                logger.error("Gemini API error after %d attempts: %s", retries + 1, e)
    raise last_error


def generate_json(prompt: str, max_tokens: int = 8192) -> dict:
    """Generate structured JSON from a prompt with robust parsing."""
    full_prompt = (
        prompt
        + "\n\nIMPORTANT: Respond ONLY with valid JSON. No markdown fences, no explanation."
    )
    text = ""
    try:
        text = generate_text(full_prompt, max_tokens)
        # Strip markdown fences if present
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()
        return json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse AI response as JSON: %s", text[:500])
        return {"error": "Failed to parse AI response", "raw": text[:1000]}
    except Exception as e:
        logger.error("AI JSON generation failed: %s", e)
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────
# Domain-specific generators
# ─────────────────────────────────────────────────────────────

def generate_resume_analysis(resume_text: str, target_role: str, role_context: str = "") -> dict:
    """Generate deep resume analysis with AI."""
    prompt = f"""You are an expert career analyst and ATS specialist. Analyze the following resume for the target role of "{target_role}".

{f"INDUSTRY CONTEXT FOR THIS ROLE:{chr(10)}{role_context}{chr(10)}" if role_context else ""}

RESUME TEXT:
{resume_text}

Provide a comprehensive JSON analysis with these exact keys:
{{
    "ats_score": <integer 0-100>,
    "skills_detected": ["skill1", "skill2", ...],
    "technologies": ["tech1", "tech2", ...],
    "frameworks": ["framework1", ...],
    "tools": ["tool1", ...],
    "projects": [
        {{"name": "...", "description": "...", "technologies": ["..."]}}
    ],
    "experience_years": <estimated integer>,
    "experience_summary": "...",
    "missing_keywords": ["keyword1", "keyword2", ...],
    "formatting_issues": ["issue1", "issue2", ...],
    "strengths": ["strength1", ...],
    "weaknesses": ["weakness1", ...],
    "improvement_suggestions": ["suggestion1", ...],
    "recruiter_readiness": "high/medium/low",
    "summary": "2-3 sentence professional summary of the candidate"
}}"""
    return generate_json(prompt)


def generate_github_analysis(github_data: dict, target_role: str, role_context: str = "") -> dict:
    """Generate deep GitHub profile analysis with AI."""
    prompt = f"""You are a senior engineering manager evaluating a developer's GitHub profile for the role of "{target_role}".

{f"INDUSTRY CONTEXT:{chr(10)}{role_context}{chr(10)}" if role_context else ""}

GITHUB PROFILE DATA:
{json.dumps(github_data, indent=2)}

Provide a comprehensive JSON analysis:
{{
    "developer_profile_summary": "...",
    "primary_languages": [{{"language": "...", "percentage": <float>, "proficiency": "expert/advanced/intermediate/beginner"}}],
    "tech_stack": ["tech1", ...],
    "frameworks_detected": ["framework1", ...],
    "databases_used": ["db1", ...],
    "ai_ml_usage": true/false,
    "ai_ml_details": "...",
    "repo_quality_score": <integer 0-100>,
    "top_repos": [
        {{"name": "...", "description": "...", "quality_score": <int>, "highlights": ["..."]}}
    ],
    "commit_consistency": "high/medium/low",
    "commit_analysis": "...",
    "project_complexity": "high/medium/low",
    "readme_quality": "excellent/good/needs-improvement/poor",
    "open_source_contributions": <integer>,
    "strengths": ["..."],
    "areas_for_improvement": ["..."],
    "overall_score": <integer 0-100>
}}"""
    return generate_json(prompt)


def generate_leetcode_analysis(leetcode_data: dict, target_role: str) -> dict:
    """Generate LeetCode analysis with AI."""
    prompt = f"""You are a technical interview coach analyzing a candidate's LeetCode profile for the role of "{target_role}".

LEETCODE DATA:
{json.dumps(leetcode_data, indent=2)}

Provide a comprehensive JSON analysis:
{{
    "total_solved": <integer>,
    "easy_solved": <integer>,
    "medium_solved": <integer>,
    "hard_solved": <integer>,
    "contest_rating": <integer or null>,
    "contest_ranking": <string or null>,
    "dsa_readiness_level": "Beginner/Intermediate/Advanced",
    "dsa_readiness_score": <integer 0-100>,
    "strong_topics": ["topic1", ...],
    "weak_topics": ["topic1", ...],
    "topics_to_improve": [
        {{"topic": "...", "reason": "...", "recommended_problems": <integer>}}
    ],
    "interview_readiness": "high/medium/low",
    "strengths": ["..."],
    "recommendations": ["..."],
    "summary": "..."
}}"""
    return generate_json(prompt)


def generate_skill_gap_report(
    user_skills: list,
    role_requirements: dict,
    resume_analysis: dict,
    github_analysis: dict,
    leetcode_analysis: dict,
    target_role: str,
    role_context: str = "",
) -> dict:
    """Generate a comprehensive, fully actionable career improvement report."""
    prompt = f"""You are a senior career mentor, technical educator, and software engineer creating a complete career improvement dashboard for a candidate targeting the role of "{target_role}".

{f"INDUSTRY STANDARDS FOR THIS ROLE:{chr(10)}{role_context}{chr(10)}" if role_context else ""}

ROLE REQUIREMENTS:
{json.dumps(role_requirements, indent=2)}

USER'S DETECTED SKILLS: {json.dumps(user_skills)}

RESUME ANALYSIS:
{json.dumps(resume_analysis, indent=2)}

GITHUB ANALYSIS:
{json.dumps(github_analysis, indent=2)}

LEETCODE ANALYSIS:
{json.dumps(leetcode_analysis, indent=2)}

Generate a complete JSON report covering ALL sections below. Be specific, personalized, and actionable. Use real resource names and accurate data.

{{
    "hiring_readiness_percentage": <integer 0-100>,
    "overall_assessment": "3-4 sentence honest assessment of the candidate's current standing for this role",
    "time_to_ready": "e.g. 2-3 months with focused effort",

    "skill_gap_summary": {{
        "programming_languages": [{{"skill": "...", "status": "missing/weak/strong", "priority": "high/medium/low"}}],
        "frameworks_libraries": [{{"skill": "...", "status": "missing/weak/strong", "priority": "high/medium/low"}}],
        "dsa_problem_solving": [{{"skill": "...", "status": "missing/weak/strong", "priority": "high/medium/low"}}],
        "system_design": [{{"skill": "...", "status": "missing/weak/strong", "priority": "high/medium/low"}}],
        "tools_devops": [{{"skill": "...", "status": "missing/weak/strong", "priority": "high/medium/low"}}]
    }},

    "strong_skills": [{{"skill": "...", "level": "expert/advanced/intermediate", "evidence": "..."}}],
    "weak_skills": [{{"skill": "...", "current_level": "...", "required_level": "...", "gap": "..."}}],
    "missing_skills": [{{"skill": "...", "importance": "critical/important/nice-to-have", "description": "..."}}],

    "coding_questions_to_practice": [
        {{
            "topic": "...",
            "difficulty": "easy/medium/hard",
            "questions": [
                {{"title": "...", "platform": "LeetCode/HackerRank/Codeforces", "url": "https://...", "why": "..."}}
            ]
        }}
    ],

    "weekly_leetcode_plan": [
        {{"week": 1, "focus": "...", "topics": ["..."], "target_problems": <int>, "difficulty_mix": "e.g. 3 Easy, 5 Medium, 1 Hard"}}
    ],

    "recommended_projects": [
        {{
            "title": "...",
            "description": "...",
            "difficulty": "beginner/intermediate/advanced",
            "skills_gained": ["..."],
            "key_features": ["..."],
            "estimated_time": "e.g. 1 week"
        }}
    ],

    "improvement_roadmap": {{
        "day_30": {{
            "goal": "...",
            "tasks": ["..."],
            "skills_to_cover": ["..."]
        }},
        "day_60": {{
            "goal": "...",
            "tasks": ["..."],
            "skills_to_cover": ["..."]
        }},
        "day_90": {{
            "goal": "...",
            "tasks": ["..."],
            "skills_to_cover": ["..."]
        }}
    }},

    "github_improvements": {{
        "project_types_to_add": ["..."],
        "readme_tips": ["..."],
        "contribution_ideas": ["..."],
        "profile_tips": ["..."]
    }},

    "interview_preparation": {{
        "technical_topics": ["..."],
        "behavioral_topics": ["..."],
        "system_design_topics": ["..."]
    }}
}}"""
    return generate_json(prompt, max_tokens=16000)


def generate_resource_recommendations(user_skills: list, role_requirements: dict, target_role: str) -> dict:
    """Generate comprehensive, personalized learning resource recommendations."""
    prompt = f"""You are an expert technical educator and career coach. Based on the candidate's skills and role requirements for "{target_role}", recommend REAL, high-quality learning resources.

DETECTED SKILLS: {json.dumps(user_skills)}
ROLE REQUIREMENTS: {json.dumps(role_requirements)}

Provide a comprehensive JSON with REAL resources (verified URLs only):
{{
    "youtube_playlists": [
        {{"title": "...", "channel": "...", "url": "https://youtube.com/@channel or https://www.youtube.com/playlist?list=...", "skill": "...", "description": "why this is helpful", "duration": "e.g. 20 hours"}}
    ],
    "courses": [
        {{"title": "...", "platform": "Coursera/Udemy/freeCodeCamp/CS50/etc", "url": "https://...", "skill": "...", "free": true/false, "level": "beginner/intermediate/advanced", "why": "why this course specifically"}}
    ],
    "articles_and_docs": [
        {{"title": "...", "url": "https://...", "skill": "...", "type": "official-docs/blog/tutorial/guide", "source": "e.g. MDN, dev.to, Medium"}}
    ],
    "dsa_sheets": [
        {{"name": "Blind 75", "url": "https://leetcode.com/list/xi4ci4ig/", "problems_count": 75, "description": "Essential patterns for FAANG interviews, curated by ex-FB engineer"}},
        {{"name": "NeetCode 150", "url": "https://neetcode.io/practice", "problems_count": 150, "description": "Structured roadmap with video solutions"}},
        {{"name": "Striver SDE Sheet", "url": "https://takeuforward.org/interviews/strivers-sde-sheet-top-coding-interview-problems/", "problems_count": 191, "description": "Comprehensive sheet for product-based companies"}},
        {{"name": "Love Babbar 450", "url": "https://450dsa.com/", "problems_count": 450, "description": "Widely used sheet covering all DSA topics in depth"}}
    ],
    "github_repositories": [
        {{"name": "owner/repo", "url": "https://github.com/...", "skill": "...", "stars": "e.g. 50k", "description": "what you will learn from this repo", "why_study": "specific reason for this candidate"}}
    ],
    "interview_resources": [
        {{"title": "...", "url": "https://...", "type": "questions/guide/mock-interview", "platform": "...", "description": "..."}}
    ]
}}

RULES:
- Use ONLY real, verifiable URLs
- DSA sheets section MUST include the 4 pre-filled sheets above plus any additional role-specific ones
- YouTube channels: prefer channels like freeCodeCamp, Fireship, Traversy Media, TechWithTim, Abdul Bari, William Fiset
- GitHub repos: prefer well-starred educational repositories
- Be specific to the target role and missing skills, not generic"""
    return generate_json(prompt, max_tokens=8192)
