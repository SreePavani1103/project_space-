"""
GitHub Service — Analyze GitHub profiles via the GitHub API.

Key optimizations:
- Thread-safe caching via functools.lru_cache on string/primitive-only functions
- fetch_repos is NOT lru_cached (returns mutable list — would error)
- fetch_languages fires all repo requests concurrently (10 workers)
- Thread-safe requests.Session per thread via threading.local()
- timeout reduced to 6s for fast failure
"""
import logging
import threading
import functools
import concurrent.futures
import requests
from flask import current_app

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"

# Thread-local session pool: each thread reuses its own HTTP connection
_thread_local = threading.local()


def _get_session() -> requests.Session:
    """Return a per-thread requests.Session with auth headers pre-set."""
    if not hasattr(_thread_local, "session") or _thread_local.session is None:
        session = requests.Session()
        token = current_app.config.get("GITHUB_TOKEN", "")
        session.headers.update({"Accept": "application/vnd.github.v3+json"})
        if token:
            session.headers.update({"Authorization": f"token {token}"})
        _thread_local.session = session
    return _thread_local.session


def _get(url, params=None):
    """Thread-safe HTTP GET with connection reuse and fast timeout."""
    try:
        session = _get_session()
        r = session.get(url, params=params, timeout=6)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        logger.warning("GitHub API timeout for %s", url)
        return None
    except Exception as e:
        logger.error("GitHub API error for %s: %s", url, e)
        return None


def extract_username(github_url: str) -> str:
    url = github_url.strip().rstrip("/")
    if "github.com/" in url:
        parts = url.split("github.com/")[-1].split("/")
        return parts[0]
    if "github/" in url:
        parts = url.split("github/")[-1].split("/")
        return parts[0]
    return url


@functools.lru_cache(maxsize=256)
def fetch_profile(username: str) -> dict:
    """Fetch and cache user profile (returns dict — safe to cache)."""
    data = _get(f"{GITHUB_API}/users/{username}")
    if not data:
        return None
    return {
        "username": data.get("login"),
        "name": data.get("name"),
        "bio": data.get("bio"),
        "public_repos": data.get("public_repos", 0),
        "followers": data.get("followers", 0),
        "following": data.get("following", 0),
        "created_at": data.get("created_at"),
        "avatar_url": data.get("avatar_url"),
        "html_url": data.get("html_url"),
    }


def fetch_repos(username: str, max_repos: int = 30) -> list:
    """
    Fetch user repos. NOT lru_cached because lists are mutable and unhashable.
    Cached at the analyze_github() level instead.
    """
    repos = _get(
        f"{GITHUB_API}/users/{username}/repos",
        params={"per_page": max_repos, "sort": "updated", "type": "owner"},
    )
    if not repos:
        return []
    result = []
    for r in repos:
        if r.get("fork"):
            continue
        result.append({
            "name": r.get("name"),
            "description": r.get("description", ""),
            "language": r.get("language"),
            "stars": r.get("stargazers_count", 0),
            "forks": r.get("forks_count", 0),
            "size": r.get("size", 0),
            "created_at": r.get("created_at"),
            "updated_at": r.get("updated_at"),
            "has_readme": True,
            "topics": r.get("topics", []),
            "html_url": r.get("html_url"),
        })
    return result


def fetch_languages(username: str, repos: list) -> dict:
    """
    Fetch language breakdown for up to 15 repos CONCURRENTLY.
    10 workers fire simultaneously — reduces 15 × 1s sequential to ~1-2s total.
    """
    lang_totals = {}

    def fetch_repo_lang(repo_name):
        return _get(f"{GITHUB_API}/repos/{username}/{repo_name}/languages")

    # Fire all language requests in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_repo_lang, repo["name"]): repo for repo in repos[:15]}
        for future in concurrent.futures.as_completed(futures):
            try:
                lang_data = future.result()
                if lang_data:
                    for lang, bytes_count in lang_data.items():
                        lang_totals[lang] = lang_totals.get(lang, 0) + bytes_count
            except Exception as e:
                logger.warning("Language fetch failed for a repo: %s", e)

    total = sum(lang_totals.values()) or 1
    return {
        lang: round(bytes_c / total * 100, 1)
        for lang, bytes_c in sorted(lang_totals.items(), key=lambda x: x[1], reverse=True)
    }


# Result-level cache: caches the full analyze_github result per URL
@functools.lru_cache(maxsize=128)
def _cached_analyze(username: str) -> dict:
    """Internal cached analysis — called by analyze_github."""
    profile = fetch_profile(username)
    if not profile:
        return {"error": f"Could not fetch GitHub profile for {username}"}

    repos = fetch_repos(username)

    # Fetch profile + repos + languages concurrently using the same executor
    languages = fetch_languages(username, repos)

    # Analyze patterns
    frameworks = set()
    databases = set()
    ai_ml = False
    topics_all = set()

    framework_keywords = {
        "react": "React", "angular": "Angular", "vue": "Vue.js", "next": "Next.js",
        "django": "Django", "flask": "Flask", "fastapi": "FastAPI", "spring": "Spring",
        "express": "Express", "rails": "Rails", "laravel": "Laravel",
        "flutter": "Flutter", "svelte": "Svelte",
    }
    db_keywords = {
        "mysql": "MySQL", "postgres": "PostgreSQL", "mongo": "MongoDB", "redis": "Redis",
        "sqlite": "SQLite", "firebase": "Firebase", "elastic": "Elasticsearch", "dynamo": "DynamoDB",
    }
    ml_keywords = [
        "tensorflow", "pytorch", "keras", "scikit", "machine-learning",
        "deep-learning", "ml", "ai", "neural", "nlp", "computer-vision",
    ]

    for repo in repos:
        desc = (repo.get("description") or "").lower()
        name = repo.get("name", "").lower()
        combined = f"{name} {desc} {' '.join(repo.get('topics', []))}"

        for kw, fw in framework_keywords.items():
            if kw in combined:
                frameworks.add(fw)
        for kw, db in db_keywords.items():
            if kw in combined:
                databases.add(db)
        for kw in ml_keywords:
            if kw in combined:
                ai_ml = True
        topics_all.update(repo.get("topics", []))

    recent_updates = [r.get("updated_at", "")[:10] for r in repos[:10] if r.get("updated_at")]
    unique_months = set(d[:7] for d in recent_updates if d)
    commit_consistency = "high" if len(unique_months) >= 4 else ("medium" if len(unique_months) >= 2 else "low")

    return {
        "profile": profile,
        "repos": repos[:15],
        "languages": languages,
        "frameworks": list(frameworks),
        "databases": list(databases),
        "ai_ml_usage": ai_ml,
        "total_repos": len(repos),
        "total_stars": sum(r.get("stars", 0) for r in repos),
        "topics": list(topics_all)[:20],
        "commit_consistency": commit_consistency,
    }


def analyze_github(github_url: str) -> dict:
    """Public entry point — extracts username and runs cached analysis."""
    username = extract_username(github_url)
    if not username:
        return {"error": "Invalid GitHub URL"}
    return _cached_analyze(username)
