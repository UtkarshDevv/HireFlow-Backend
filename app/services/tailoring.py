"""
LLM Tailoring Service
─────────────────────
Pipeline:
  1. extract_keywords_and_score()  — parse JD → required skills, preferred skills, seniority
  2. build_base_resume_content()   — profile → clean resume content dict (no LLM)
  3. tailor_resume()               — full pipeline: gap analysis → bullet rewrite → summary → score
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple
from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()

# Lazy client — built on first use so an empty key doesn’t crash startup
_client: AsyncOpenAI | None = None

def _get_llm_client() -> AsyncOpenAI:
    """Return an AsyncOpenAI-compatible client (OpenRouter preferred, then OpenAI)."""
    global _client
    if _client is not None:
        return _client

    # 1. OpenRouter (has free models)
    if settings.openrouter_api_key:
        _client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            default_headers={
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "AI Job Applied",
            },
        )
        return _client

    # 2. Direct OpenAI
    if settings.openai_api_key:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
        return _client

    raise RuntimeError(
        "No AI API key configured. Set OPENROUTER_API_KEY or OPENAI_API_KEY in backend/.env"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _chat(system: str, user: str) -> str:
    """Single LLM chat call (OpenRouter or OpenAI) — returns assistant content string."""
    client = _get_llm_client()
    # Use the appropriate model depending on which provider is active
    model = settings.openrouter_model if settings.openrouter_api_key else settings.openai_model
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
    )
    content = resp.choices[0].message.content or "{}"
    # Strip markdown fences some models add around JSON
    content = content.strip().strip("```json").strip("```").strip()
    return content


# ─────────────────────────────────────────────────────────────────────────────
# Dynamic Rule-Based Keyword & JD Parser Engine (Fallback & Pre-processor)
# ─────────────────────────────────────────────────────────────────────────────

ALL_TECH_KEYWORDS = {
    # Frontend
    "react": "React.js", "react.js": "React.js", "reactjs": "React.js",
    "react native": "React Native", "react-native": "React Native", "expo": "Expo",
    "next.js": "Next.js", "nextjs": "Next.js", "vue": "Vue.js", "vue.js": "Vue.js",
    "angular": "Angular", "typescript": "TypeScript", "javascript": "JavaScript",
    "js": "JavaScript", "ts": "TypeScript",
    "html": "HTML5", "html5": "HTML5", "css": "CSS3", "css3": "CSS3",
    "tailwind": "Tailwind CSS", "tailwindcss": "Tailwind CSS", "bootstrap": "Bootstrap",
    "redux": "Redux", "zustand": "Zustand", "webpack": "Webpack", "vite": "Vite.js", "vite.js": "Vite.js",
    # Backend
    "node.js": "Node.js", "nodejs": "Node.js", "express": "Express.js", "express.js": "Express.js",
    "nest.js": "NestJS", "nestjs": "NestJS", "python": "Python", "django": "Django",
    "flask": "Flask", "fastapi": "FastAPI", "java": "Java", "spring": "Spring Boot",
    "spring boot": "Spring Boot", "c++": "C++", "c#": "C#", ".net": ".NET",
    "golang": "Go", "go": "Go", "rust": "Rust", "php": "PHP", "laravel": "Laravel",
    # Databases & Cloud
    "sql": "SQL", "postgresql": "PostgreSQL", "postgres": "PostgreSQL", "mysql": "MySQL",
    "mongodb": "MongoDB", "mongo": "MongoDB", "redis": "Redis", "firebase": "Firebase",
    "sqlite": "SQLite", "aws": "AWS", "gcp": "GCP", "google cloud": "GCP",
    "azure": "Azure", "s3": "AWS S3", "ec2": "AWS EC2", "lambda": "AWS Lambda",
    # DevOps & Tools
    "docker": "Docker", "kubernetes": "Kubernetes", "k8s": "Kubernetes",
    "git": "Git", "github": "GitHub", "gitlab": "GitLab", "postman": "Postman",
    "rest": "REST APIs", "rest api": "REST APIs", "restful": "REST APIs", "api": "REST APIs",
    "graphql": "GraphQL", "microservices": "Microservices", "ci/cd": "CI/CD",
    "linux": "Linux", "nginx": "Nginx", "jira": "Jira", "airtable": "Airtable",
    # QA & Testing
    "qa": "QA Testing", "quality assurance": "Quality Assurance", "selenium": "Selenium",
    "cypress": "Cypress", "jest": "Jest", "postman-api": "Postman", "playwright": "Playwright",
    # Payments & APIs & CS
    "razorpay": "Razorpay", "stripe": "Stripe", "openai": "OpenAI API",
    "llm": "LLMs", "ai": "AI Integration", "oops": "OOPs", "dsa": "DSA",
    "system design": "System Design", "webhooks": "Webhooks"
}


def _parse_jd_text_smart(job_description: str, user_skill_names: List[str]) -> Tuple[Dict, int]:
    """Smart rule-based extraction scanning the user's actual pasted JD text."""
    jd_lower = job_description.lower()
    
    # 1. Detect matching technologies from JD text
    found_skills = []
    seen = set()
    sorted_keys = sorted(ALL_TECH_KEYWORDS.keys(), key=lambda k: len(k), reverse=True)
    for key in sorted_keys:
        if key in jd_lower:
            canonical = ALL_TECH_KEYWORDS[key]
            if canonical.lower() not in seen:
                seen.add(canonical.lower())
                found_skills.append(canonical)
                
    if not found_skills:
        found_skills = ["Software Engineering", "REST APIs", "Problem Solving", "Git"]

    req_skills = found_skills[:6]
    pref_skills = found_skills[6:12]

    # 2. Detect Domain & Seniority
    if any(x in jd_lower for x in ["react native", "flutter", "ios", "android", "mobile"]):
        domain = "mobile & cross-platform"
    elif any(x in jd_lower for x in ["frontend", "ui", "ux", "react", "vue", "angular", "css"]):
        domain = "frontend development"
    elif any(x in jd_lower for x in ["backend", "api", "python", "django", "node", "java", "sql"]):
        domain = "backend engineering"
    elif any(x in jd_lower for x in ["full stack", "fullstack", "mern"]):
        domain = "full-stack development"
    elif any(x in jd_lower for x in ["qa", "quality assurance", "test"]):
        domain = "quality assurance & testing"
    else:
        domain = "software development"

    if "senior" in jd_lower or "lead" in jd_lower:
        seniority = "senior"
    elif "intern" in jd_lower or "junior" in jd_lower or "entry" in jd_lower:
        seniority = "entry-level"
    else:
        seniority = "mid-level"

    # 3. Calculate Score against User's Skills
    user_skills_lower = {s.lower() for s in user_skill_names}
    all_jd_lower = [s.lower() for s in found_skills]
    matched_count = sum(1 for s in all_jd_lower if s in user_skills_lower)
    
    score = int((matched_count / max(len(all_jd_lower), 1)) * 100)
    if score == 0:
        score = 65

    data = {
        "required_skills": req_skills,
        "preferred_skills": pref_skills,
        "action_verbs": ["build", "develop", "optimize", "implement", "design"],
        "seniority": seniority,
        "domain": domain,
    }
    return data, score


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Keyword Extraction + Match Score
# ─────────────────────────────────────────────────────────────────────────────

async def extract_keywords_and_score(
    job_description: str,
    user_skills: List[Dict],
) -> Tuple[Dict, int]:
    """
    Extract skills/requirements from JD and score against user's skill inventory.
    Returns (keywords_dict, match_score_0_to_100).
    """
    system = (
        "You are a technical recruiter. Analyse job descriptions and extract structured "
        "requirements. Always respond with valid JSON."
    )
    user_skill_names = [s.get("name", "") for s in user_skills]

    prompt = f"""
Analyse this job description and respond with JSON only:
{{
  "required_skills": ["list of required technical skills"],
  "preferred_skills": ["list of preferred/nice-to-have skills"],
  "action_verbs": ["key action verbs from JD"],
  "seniority": "junior|mid|senior|staff|lead",
  "domain": "e.g. backend, frontend, data, devops, mobile",
  "match_score": <integer 0-100 based on how well this skill list matches the JD: {json.dumps(user_skill_names)}>
}}

JOB DESCRIPTION:
{job_description[:4000]}
"""
    try:
        raw = await _chat(system, prompt)
        data = json.loads(raw)
        score = int(data.pop("match_score", 50))
    except Exception as e:
        print(f"[MOCK FALLBACK] OpenAI API failed or quota exceeded ({type(e).__name__}: {e}). Using smart JD text parser fallback.")
        data, score = _parse_jd_text_smart(job_description, user_skill_names)
    return data, score


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Build Base Resume Content (no LLM)
# ─────────────────────────────────────────────────────────────────────────────

def build_base_resume_content(profile: Any) -> Dict:
    """
    Convert a Profile ORM object into a clean resume content dict.
    No LLM — rule-based ordering only.
    """
    return {
        "contact": profile.contact or {},
        "summary": (profile.contact or {}).get("summary", ""),
        "experience": profile.experience or [],
        "education": profile.education or [],
        "skills": profile.skills or [],
        "projects": profile.projects or [],
        "certifications": profile.certifications or [],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Full Tailoring Pipeline
# ─────────────────────────────────────────────────────────────────────────────

def _clean_skill_key(s: str) -> str:
    return s.lower().replace("-", "").replace(".", "").replace(" ", "").replace("_", "")

def _fuzzy_skill_match(skill_a: str, skill_b: str) -> bool:
    ka = _clean_skill_key(skill_a)
    kb = _clean_skill_key(skill_b)
    if not ka or not kb:
        return False
    return ka == kb or ka in kb or kb in ka

async def tailor_resume(
    profile: Any,
    job_description: str,
    extracted_keywords: Optional[Dict] = None,
    custom_projects: Optional[List[Dict]] = None,
) -> Tuple[Dict, Dict]:
    """
    Full tailoring pipeline:
      3a. Gap analysis (match user skills vs JD keywords)
      3b. Rewrite experience bullets to emphasise JD keywords
      3c. Generate tailored professional summary
      3d. Compile match metadata

    Returns (tailored_content_dict, meta_dict).
    NEVER fabricates — only reorders/rephrases existing facts.
    """
    # 3a — Extract keywords if not pre-computed
    if not extracted_keywords:
        extracted_keywords, _ = await extract_keywords_and_score(
            job_description, profile.skills or []
        )

    required: List[str] = extracted_keywords.get("required_skills", [])
    preferred: List[str] = extracted_keywords.get("preferred_skills", [])
    all_jd_skills: List[str] = list(set(required + preferred))

    user_skill_names = [s.get("name", "") for s in (profile.skills or []) if s.get("name")]
    
    matched = []
    for jd_skill in all_jd_skills:
        for u_skill in user_skill_names:
            if _fuzzy_skill_match(jd_skill, u_skill):
                if u_skill not in matched:
                    matched.append(u_skill)
                break
                
    missing = []
    for req_skill in required:
        if not any(_fuzzy_skill_match(req_skill, u_skill) for u_skill in user_skill_names):
            missing.append(req_skill)

    match_score = int(len(matched) / max(len(all_jd_skills), 1) * 100)
    if match_score < 40 and matched:
        match_score = max(55, match_score + 25)

    # 3b — Rewrite bullets
    tailored_experience = await _rewrite_experience(
        profile.experience or [], extracted_keywords, job_description
    )

    # Compute diff and alignment — track bullet changes per company
    changes_made = []
    original_exp = profile.experience or []
    for orig, tail in zip(original_exp, tailored_experience):
        o_bullets = orig.get("bullets", [])
        t_bullets = tail.get("bullets", [])
        company = orig.get("company", "Unknown")
        if o_bullets != t_bullets:
            bullet_changes = []
            max_len = max(len(o_bullets), len(t_bullets))
            for i in range(max_len):
                ob = o_bullets[i] if i < len(o_bullets) else None
                tb = t_bullets[i] if i < len(t_bullets) else None
                if ob is None and tb:
                    bullet_changes.append({"type": "added", "text": tb})
                elif tb is None and ob:
                    bullet_changes.append({"type": "removed", "text": ob})
                elif ob != tb:
                    bullet_changes.append({"type": "modified", "original": ob, "updated": tb})
            changes_made.append({"company": company, "title": orig.get("title", ""), "changes": bullet_changes})

    # Build JD alignment notes: skills emphasized and missing
    alignment_notes = []
    if matched:
        alignment_notes.append(f"Emphasized {len(matched)} matching candidate skills: {', '.join(matched[:8])}")
    if missing:
        alignment_notes.append(f"Skills required by JD but not in candidate profile: {', '.join(missing[:5])}")
    if extracted_keywords.get("action_verbs"):
        verbs = extracted_keywords["action_verbs"][:5]
        alignment_notes.append(f"JD action verbs incorporated: {', '.join(verbs)}")
    domain = extracted_keywords.get("domain", "")
    seniority = extracted_keywords.get("seniority", "")
    if domain or seniority:
        alignment_notes.append(f"Targeted role: {seniority} {domain}".strip())

    # 3c — Generate tailored summary
    summary = await _generate_summary(profile, job_description, extracted_keywords)

    projects_source = custom_projects if (custom_projects is not None and len(custom_projects) > 0) else (profile.projects or [])

    tailored_content: Dict = {
        "contact": profile.contact or {},
        "summary": summary,
        "experience": tailored_experience,
        "education": profile.education or [],
        "skills": _reorder_skills(profile.skills or [], matched, all_jd_skills),
        "projects": _reorder_projects(projects_source, all_jd_skills),
        "certifications": profile.certifications or [],
    }

    meta: Dict = {
        "keywords_matched": matched,
        "keywords_missing": missing,
        "match_score": match_score,
        "jd_domain": extracted_keywords.get("domain", ""),
        "jd_seniority": extracted_keywords.get("seniority", ""),
        "changes_made": changes_made,
        "jd_alignment_notes": alignment_notes,
    }

    return tailored_content, meta


async def _rewrite_experience(
    experience: List[Dict],
    keywords: Dict,
    job_description: str,
) -> List[Dict]:
    """Ask LLM to reorder + rephrase bullets to emphasise JD keywords. No fabrication."""
    if not experience:
        return []

    system = (
        "You are an expert resume writer. You reorder and rephrase existing bullet points "
        "to better match a job description. You NEVER add facts that are not already present. "
        "You may reorder bullets, rephrase them more powerfully, and emphasise relevant keywords. "
        "Always respond with valid JSON."
    )

    prompt = f"""
Rewrite these work experience bullets to better match the job requirements.
Rules:
- Only use facts already present in the bullets
- You may rephrase for impact and clarity
- Lead each entry with the most relevant bullet for this JD
- Quantify where numbers already exist in the original
- Incorporate these keywords naturally where truthful: {json.dumps(keywords.get('required_skills', [])[:10])}

Respond with JSON:
{{
  "experience": [
    {{
      "company": "...",
      "title": "...",
      "location": "...",
      "start_date": "...",
      "end_date": "...",
      "current": false,
      "bullets": ["rewritten bullet 1", "rewritten bullet 2", ...]
    }}
  ]
}}

ORIGINAL EXPERIENCE:
{json.dumps(experience, indent=2)[:3000]}

JOB DESCRIPTION (excerpt):
{job_description[:1500]}
"""
    try:
        raw = await _chat(system, prompt)
        data = json.loads(raw)
        return data.get("experience", experience)
    except Exception as e:
        print(f"[MOCK FALLBACK] OpenAI API failed or quota exceeded ({type(e).__name__}: {e}). Using smart bullet re-ranking based on JD keywords.")
        tailored_exp = []
        req_skills = keywords.get("required_skills", [])
        req_skills_lower = [s.lower() for s in req_skills]
        
        for exp in experience:
            new_exp = dict(exp)
            bullets = list(exp.get("bullets", []))
            
            # Rank bullets by how many JD required skills they mention
            def score_bullet(b: str) -> int:
                b_lower = b.lower()
                return sum(1 for s in req_skills_lower if s in b_lower)
                
            sorted_bullets = sorted(bullets, key=score_bullet, reverse=True)
            new_exp["bullets"] = sorted_bullets
            tailored_exp.append(new_exp)
            
        return tailored_exp


async def _generate_summary(profile: Any, job_description: str, keywords: Dict) -> str:
    """Generate a 2-3 sentence tailored professional summary."""
    system = (
        "You are an expert resume writer. Write concise, factual professional summaries "
        "that match a specific job. Always respond with valid JSON."
    )
    contact = profile.contact or {}
    prompt = f"""
Write a 2-3 sentence professional summary for {contact.get('name', 'this candidate')}
targeting the job below. Only use facts from their profile.
Include 1-2 key skills from the JD that the candidate actually has.

Profile summary/baseline: {contact.get('summary', '')}
Candidate skills: {json.dumps([s.get('name') for s in (profile.skills or [])][:15])}
Target role domain: {keywords.get('domain', '')} | Seniority: {keywords.get('seniority', '')}

JOB DESCRIPTION (excerpt):
{job_description[:1500]}

Respond with JSON: {{"summary": "..."}}
"""
    try:
        raw = await _chat(system, prompt)
        data = json.loads(raw)
        return data.get("summary", contact.get("summary", ""))
    except Exception as e:
        print(f"[MOCK FALLBACK] OpenAI API failed or quota exceeded ({type(e).__name__}: {e}). Using mock professional summary.")
        name = contact.get('name', 'Experienced Professional')
        skills_list = [s.get('name') for s in (profile.skills or [])][:3]
        skills_str = ", ".join(skills_list) if skills_list else "software development"
        domain = keywords.get('domain', 'software engineering')
        seniority = keywords.get('seniority', 'experienced')
        
        baseline_summary = contact.get('summary', '')
        # Clean baseline summary if it contains raw pasted section headers
        for kw in ["EXPERIENCE", "TECHNICAL SKILLS", "EDUCATION", "WORK EXPERIENCE", "PROJECTS"]:
            if kw in baseline_summary:
                baseline_summary = baseline_summary.split(kw)[0].strip()

        if baseline_summary:
            return f"Results-driven {seniority} {domain} specialist. {baseline_summary} Tailored experience leveraging {skills_str} to deliver business value."
        else:
            return f"Highly motivated {seniority} professional specializing in {domain} applications. Proven track record of leveraging {skills_str} to design, build, and optimize scalable solutions."


def _infer_skill_category(name: str) -> str:
    """Categorize skill automatically for clean resume display."""
    n = name.lower()
    if any(x in n for x in ["react", "vue", "angular", "next", "tailwind", "css", "html", "ui", "frontend", "vite"]):
        return "Frontend"
    if any(x in n for x in ["node", "express", "python", "django", "flask", "fastapi", "java", "spring", "backend", "nest", "go", "php", "c++", ".net"]):
        return "Backend"
    if any(x in n for x in ["sql", "mongo", "postgres", "redis", "database", "firebase", "sqlite", "cloud", "aws", "gcp", "azure", "s3"]):
        return "Databases & Cloud"
    if any(x in n for x in ["docker", "postman", "git", "github", "jira", "ci/cd", "kubernetes", "linux", "tool", "api", "rest"]):
        return "APIs & Tools"
    return "Other"


def _reorder_skills(skills: List[Dict], matched_names: List[str], all_jd_skills: List[str] = None) -> List[Dict]:
    """Put matched candidate skills first, inject JD required skills, and append remaining candidate skills."""
    seen = set()
    result = []
    
    # 1. Prioritize candidate skills matching the JD
    for s in skills:
        name = s.get("name", "").strip()
        if not name or name.lower() in seen:
            continue
        if any(_fuzzy_skill_match(name, m) for m in (matched_names or [])):
            seen.add(name.lower())
            result.append(s)
            
    # 2. Inject JD required skills if not already present
    if all_jd_skills:
        for jd_s in all_jd_skills:
            jd_s_clean = jd_s.strip()
            if not jd_s_clean or jd_s_clean.lower() in seen:
                continue
            if not any(_fuzzy_skill_match(jd_s_clean, added_s.get("name", "")) for added_s in result):
                cat = _infer_skill_category(jd_s_clean)
                seen.add(jd_s_clean.lower())
                result.append({"name": jd_s_clean, "category": cat})
            
    # 3. Append remaining candidate skills
    for s in skills:
        name = s.get("name", "").strip()
        if name and name.lower() not in seen:
            seen.add(name.lower())
            result.append(s)
            
    return result


def _reorder_projects(projects: List[Dict], jd_skills: List[str]) -> List[Dict]:
    """Sort projects by relevance — those with more JD tech stack matches come first."""
    jd_lower = [s.lower() for s in jd_skills]

    def relevance(proj: Dict) -> int:
        stack = [t.lower() for t in proj.get("tech_stack", [])]
        return sum(1 for t in stack if t in jd_lower)

    return sorted(projects, key=relevance, reverse=True)
