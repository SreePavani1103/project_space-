"""
Skill Gap Service — Compare user skills against role requirements using semantic similarity.
"""
import logging

logger = logging.getLogger(__name__)

# Global model instance for lazy loading
_model = None


def get_embedding_model():
    """Load the SentenceTransformer model once and cache it."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            # Lightweight model: ~80MB, fast inference on CPU
            _model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Semantic Matching: Model 'all-MiniLM-L6-v2' loaded successfully.")
        except Exception as e:
            logger.error(f"Semantic Matching: Failed to load model, falling back to string matching. Error: {e}")
            return None
    return _model


def semantic_skill_match(user_skills: list, required_skills: list, threshold: float = 0.7) -> tuple:
    """
    Compare user skills to required skills using semantic similarity.
    Returns (strong_skills, missing_skills, extra_skills).
    """
    model = get_embedding_model()
    
    # Fallback to simple string comparison if model isn't available
    if not model:
        user_lower = [s.lower() for s in user_skills]
        strong = [s for s in required_skills if s.lower() in user_lower]
        missing = [s for s in required_skills if s.lower() not in user_lower]
        extra = [s for s in user_skills if s.lower() not in [r.lower() for r in required_skills]]
        return strong, missing, extra

    if not required_skills:
        return [], [], user_skills
    if not user_skills:
        return [], required_skills, []

    try:
        from sentence_transformers import util
        # 1. Generate embeddings
        user_embeddings = model.encode(user_skills, convert_to_tensor=True, show_progress_bar=False)
        req_embeddings = model.encode(required_skills, convert_to_tensor=True, show_progress_bar=False)

        # 2. Compute cosine similarity matrix (Rows: Required, Cols: User)
        cosine_scores = util.cos_sim(req_embeddings, user_embeddings)
        
        strong = []
        missing = []
        matched_user_indices = set()

        # 3. Analyze matches
        for i, req_skill in enumerate(required_skills):
            # Find the best match score for this required skill across all user skills
            scores = cosine_scores[i]
            best_score = float(scores.max())
            best_idx = int(scores.argmax())

            if best_score >= threshold:
                strong.append(req_skill)
                matched_user_indices.add(best_idx)
            else:
                missing.append(req_skill)

        # Extra skills are user skills that didn't semantically match any required skill
        extra = [user_skills[j] for j in range(len(user_skills)) if j not in matched_user_indices]
        
        return strong, missing, extra

    except Exception as e:
        logger.error(f"Semantic Matching: Error during inference: {e}")
        # Final fallback
        user_lower = [s.lower() for s in user_skills]
        return ([s for s in required_skills if s.lower() in user_lower],
                [s for s in required_skills if s.lower() not in user_lower],
                [s for s in user_skills if s.lower() not in [r.lower() for r in required_skills]])


def compute_skill_gap(user_skills: list, role_data: dict) -> dict:
    """Compare user skills against role requirements and compute gap analysis."""
    if not role_data:
        return {"error": "No role data available"}

    required = role_data.get("required_skills", [])
    
    # Use semantic matching instead of simple string intersection
    strong, missing, extra = semantic_skill_match(user_skills, required)

    coverage = len(strong) / max(len(required), 1) * 100
    
    # Hiring readiness combines coverage and extra relevant skills
    # Caps at 100
    hiring_readiness = int(min(int(coverage * 0.8) + len(extra), 100))

    return {
        "role": role_data.get("role", "Unknown"),
        "required_skills": required,
        "strong_skills": strong,
        "missing_skills": missing,
        "extra_skills": extra,
        "coverage_percentage": round(coverage, 1),
        "hiring_readiness": hiring_readiness,
        "interview_topics": role_data.get("interview_topics", []),
        "hiring_expectations": role_data.get("hiring_expectations", {}),
        "industry_standards": role_data.get("industry_standards", []),
    }
