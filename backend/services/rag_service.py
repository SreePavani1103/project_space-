"""
RAG Service — ChromaDB integration for Retrieval-Augmented Generation.
"""
import json
import logging
import os
import threading

logger = logging.getLogger(__name__)

_client = None
_collection = None
_init_lock = threading.Lock()  # BUG 2 FIX: guards against race condition in parallel workers


def _get_collection():
    global _client, _collection
    # BUG 2 FIX: double-checked locking to prevent concurrent init in ThreadPoolExecutor
    if _collection is None:
        with _init_lock:
            if _collection is None:  # re-check inside lock
                import chromadb
                try:
                    from flask import current_app
                    persist_dir = current_app.config.get("CHROMA_PERSIST_DIR", os.getenv("CHROMA_PERSIST_DIR", "./chromadb"))
                except RuntimeError:
                    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chromadb")
                os.makedirs(persist_dir, exist_ok=True)
                _client = chromadb.PersistentClient(path=persist_dir)
                _collection = _client.get_or_create_collection(
                    name="skill_synth_kb", metadata={"hnsw:space": "cosine"},
                )
                logger.info("ChromaDB collection ready — %d documents", _collection.count())
    return _collection


ROLE_KNOWLEDGE_BASE = {
    "backend_developer": {
        "role": "Backend Developer",
        "required_skills": ["Python","Java","Node.js","SQL","PostgreSQL","MongoDB","REST APIs","GraphQL","Docker","Kubernetes","Redis","Message Queues","Microservices","CI/CD","Git","Authentication/Authorization","Testing","System Design"],
        "interview_topics": ["DSA","System Design","Database Design","API Design","Caching","Concurrency","Security","Performance Optimization"],
        "hiring_expectations": {"junior":"One backend language, basic SQL, REST APIs, Git","mid":"2+ languages, DB design, Docker, testing, CI/CD","senior":"System design, microservices, leadership, architecture"},
        "industry_standards": ["Scalable API design","12-factor apps","Clean architecture","Comprehensive testing","Monitoring","Security-first"],
        "learning_resources": ["System Design Primer","Backend Roadmap","Designing Data-Intensive Applications","Docker docs"]
    },
    "frontend_developer": {
        "role": "Frontend Developer",
        "required_skills": ["HTML5","CSS3","JavaScript","TypeScript","React","Vue.js","Angular","Next.js","Responsive Design","State Management","REST APIs","GraphQL","Testing","Webpack/Vite","Git","Accessibility"],
        "interview_topics": ["JS Fundamentals","DOM","CSS Layout","Component Architecture","State Management","Performance","Browser APIs","Accessibility"],
        "hiring_expectations": {"junior":"HTML/CSS/JS, one framework, responsive design","mid":"Deep framework knowledge, state management, TypeScript","senior":"Architecture, performance optimization, mentoring"},
        "industry_standards": ["Component-driven dev","Mobile-first design","Lighthouse > 90","WCAG 2.1 AA","Comprehensive testing"],
        "learning_resources": ["MDN Web Docs","Frontend Masters","React Docs","CSS Tricks","Web.dev"]
    },
    "full_stack_developer": {
        "role": "Full Stack Developer",
        "required_skills": ["HTML5","CSS3","JavaScript","TypeScript","React","Node.js","Python","SQL","NoSQL","REST APIs","GraphQL","Docker","Git","CI/CD","Cloud Services","Authentication","Testing","System Design"],
        "interview_topics": ["Full app architecture","Database design","API design","Frontend frameworks","Backend patterns","DevOps","System Design","DSA"],
        "hiring_expectations": {"junior":"Simple full-stack apps, basic DB, REST APIs","mid":"Production-ready apps, testing, deployment","senior":"Architecture, scalability, leadership"},
        "industry_standards": ["End-to-end feature ownership","Clean code","DevOps culture","Agile","Code review"],
        "learning_resources": ["Full Stack Open","The Odin Project","FreeCodeCamp"]
    },
    "data_scientist": {
        "role": "Data Scientist",
        "required_skills": ["Python","R","SQL","Pandas","NumPy","Scikit-learn","TensorFlow","PyTorch","Statistics","ML","Deep Learning","NLP","Data Visualization","Jupyter","Git","A/B Testing"],
        "interview_topics": ["Statistics","ML Algorithms","Feature Engineering","Model Evaluation","SQL","Experimental Design","Business Cases"],
        "hiring_expectations": {"junior":"Strong stats, Python, basic ML, SQL","mid":"Advanced ML, deep learning, production pipelines","senior":"Research, novel solutions, ML system design"},
        "industry_standards": ["Reproducible experiments","Model monitoring","Ethical AI","Business impact measurement"],
        "learning_resources": ["Andrew Ng ML Course","Fast.ai","Kaggle","Hands-On ML book"]
    },
    "devops_engineer": {
        "role": "DevOps Engineer",
        "required_skills": ["Linux","Docker","Kubernetes","CI/CD","Jenkins","GitHub Actions","Terraform","Ansible","AWS","GCP","Azure","Monitoring","Prometheus","Grafana","Bash","Python","Networking","Security","Git"],
        "interview_topics": ["IaC","Container Orchestration","CI/CD Design","Cloud Architecture","Monitoring","Security","Incident Management","Networking"],
        "hiring_expectations": {"junior":"Linux, Docker, basic CI/CD, one cloud","mid":"Kubernetes, IaC, multi-cloud, monitoring","senior":"Platform engineering, SRE, cost optimization"},
        "industry_standards": ["GitOps","IaC","Zero-downtime deployments","Monitoring","DR planning"],
        "learning_resources": ["DevOps Roadmap","K8s Docs","AWS/GCP free tier","Linux Academy"]
    },
    "mobile_developer": {
        "role": "Mobile Developer",
        "required_skills": ["React Native","Flutter","Swift","Kotlin","Java","iOS","Android","REST APIs","State Management","UI/UX","Firebase","Push Notifications","App Store","Testing","Git"],
        "interview_topics": ["Mobile Architecture","Platform APIs","Cross-platform","Performance","UI/UX","App Lifecycle","Data Persistence","Security"],
        "hiring_expectations": {"junior":"One platform, basic publishing, UI components","mid":"Cross-platform, complex state, CI/CD for mobile","senior":"Architecture, performance, platform-specific depth"},
        "industry_standards": ["Material Design/HIG","Offline-first","Accessibility","ASO","Analytics"],
        "learning_resources": ["Flutter Docs","React Native Docs","Ray Wenderlich","Android Developers"]
    },
    "ml_engineer": {
        "role": "Machine Learning Engineer",
        "required_skills": ["Python","TensorFlow","PyTorch","Scikit-learn","MLOps","Docker","Kubernetes","AWS SageMaker","Data Pipelines","Feature Stores","Model Serving","SQL","Spark","Git","CI/CD"],
        "interview_topics": ["ML System Design","Training at Scale","Feature Engineering","Deployment","Monitoring","Data Pipelines","DSA"],
        "hiring_expectations": {"junior":"ML fundamentals, Python, basic deployment","mid":"Production ML, MLOps, distributed training","senior":"ML architecture, research-to-production, leadership"},
        "industry_standards": ["Experiment tracking","Model versioning","Auto retraining","Data quality monitoring"],
        "learning_resources": ["Made With ML","Full Stack Deep Learning","MLOps Community"]
    },
    "cybersecurity_analyst": {
        "role": "Cybersecurity Analyst",
        "required_skills": ["Network Security","SIEM","Pen Testing","Incident Response","Vulnerability Assessment","Firewalls","IDS/IPS","Python","Bash","Wireshark","Nmap","OWASP","Compliance","Cloud Security","Cryptography"],
        "interview_topics": ["OWASP Top 10","Incident Response","Network Protocols","Cryptography","Threat Modeling","Security Frameworks"],
        "hiring_expectations": {"junior":"Security fundamentals, basic tools, Security+","mid":"Advanced pen testing, SIEM, incident handling","senior":"Security architecture, compliance, red/blue team"},
        "industry_standards": ["Defense in depth","Zero trust","Continuous monitoring","Compliance"],
        "learning_resources": ["TryHackMe","HackTheBox","OWASP","CompTIA certs"]
    },
    "cloud_architect": {
        "role": "Cloud Architect",
        "required_skills": ["AWS","Azure","GCP","Terraform","CloudFormation","Kubernetes","Docker","Networking","Security","Serverless","Microservices","Cost Optimization","HA","DR","CI/CD","Python","IaC"],
        "interview_topics": ["Cloud Architecture","Multi-cloud","Cost Optimization","Security","HA Design","Migration","Serverless"],
        "hiring_expectations": {"junior":"One cloud cert, basic IaC","mid":"Multi-cloud, complex architectures, cost management","senior":"Enterprise architecture, governance, innovation"},
        "industry_standards": ["Well-Architected Framework","Cloud-native","FinOps","Security by default"],
        "learning_resources": ["AWS SA path","Google Cloud training","A Cloud Guru"]
    },
    "software_engineer": {
        "role": "Software Engineer",
        "required_skills": ["Python","Java","C++","JavaScript","SQL","Git","Data Structures","Algorithms","System Design","OOP","REST APIs","Testing","CI/CD","Docker","Agile/Scrum"],
        "interview_topics": ["DSA","System Design","OOP Design","Behavioral","Coding Problems","Architecture Patterns"],
        "hiring_expectations": {"junior":"CS fundamentals, one language, basic DSA","mid":"Multiple languages, system design basics, production exp","senior":"Architecture, mentoring, cross-team, tech leadership"},
        "industry_standards": ["Clean code","SOLID principles","TDD","Agile","Code review culture"],
        "learning_resources": ["LeetCode","System Design Primer","Clean Code book","CLRS"]
    },
}


def seed_knowledge_base():
    collection = _get_collection()
    if collection.count() > 0:
        return collection.count()
    documents, metadatas, ids = [], [], []
    for rk, rd in ROLE_KNOWLEDGE_BASE.items():
        doc = f"Role: {rd['role']}\nRequired Skills: {', '.join(rd['required_skills'])}\nInterview Topics: {', '.join(rd['interview_topics'])}\nIndustry Standards: {', '.join(rd['industry_standards'])}"
        documents.append(doc)
        metadatas.append({"role_key": rk, "role_name": rd["role"], "type": "role_profile", "skills_json": json.dumps(rd["required_skills"])})
        ids.append(f"role_{rk}")
    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    logger.info("Seeded %d role profiles.", len(documents))
    return len(documents)


def _keyword_fallback(target_role):
    """Simple keyword match against the in-memory knowledge base."""
    target_lower = target_role.lower().replace(" ", "_")
    # Direct key match
    if target_lower in ROLE_KNOWLEDGE_BASE:
        rd = ROLE_KNOWLEDGE_BASE[target_lower]
        return {"found": True, "context": f"Role: {rd['role']}\nRequired Skills: {', '.join(rd['required_skills'])}",
                "role_data": rd, "matched_role": rd["role"], "distance": 0.0}
    # Partial match on role name
    for rk, rd in ROLE_KNOWLEDGE_BASE.items():
        if target_lower in rk or target_lower in rd["role"].lower():
            return {"found": True, "context": f"Role: {rd['role']}\nRequired Skills: {', '.join(rd['required_skills'])}",
                    "role_data": rd, "matched_role": rd["role"], "distance": 0.5}
    return {"found": False, "context": "", "role_data": None, "matched_role": "", "distance": 2.0}


def query_role(target_role, n_results=3):
    try:
        collection = _get_collection()
        if collection.count() == 0:
            seed_knowledge_base()
        results = collection.query(query_texts=[target_role], n_results=min(n_results, max(collection.count(), 1)), include=["documents","metadatas","distances"])
        if not results["documents"] or not results["documents"][0]:
            return _keyword_fallback(target_role)
        best_meta = results["metadatas"][0][0]
        best_distance = results["distances"][0][0]
        found = best_distance < 1.2
        role_data = ROLE_KNOWLEDGE_BASE.get(best_meta.get("role_key")) if found else None
        context = "\n\n---\n\n".join(results["documents"][0])
        return {"found": found, "context": context, "role_data": role_data, "matched_role": best_meta.get("role_name", ""), "distance": best_distance}
    except Exception as e:
        logger.warning("ChromaDB query failed, using keyword fallback: %s", e)
        return _keyword_fallback(target_role)


def add_role(role_key, role_data):
    collection = _get_collection()
    doc = f"Role: {role_data.get('role', role_key)}\nRequired Skills: {', '.join(role_data.get('required_skills', []))}"
    collection.upsert(documents=[doc], metadatas=[{"role_key": role_key, "role_name": role_data.get("role", role_key), "type": "role_profile", "skills_json": json.dumps(role_data.get("required_skills", []))}], ids=[f"role_{role_key}"])
    ROLE_KNOWLEDGE_BASE[role_key] = role_data


def get_all_roles():
    return [{"key": k, "name": v["role"], "skills_count": len(v["required_skills"])} for k, v in ROLE_KNOWLEDGE_BASE.items()]


def get_role_details(role_key):
    return ROLE_KNOWLEDGE_BASE.get(role_key)


def get_kb_stats():
    collection = _get_collection()
    return {"total_documents": collection.count(), "total_roles": len(ROLE_KNOWLEDGE_BASE), "roles": list(ROLE_KNOWLEDGE_BASE.keys())}
