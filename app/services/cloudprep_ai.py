"""
CloudPrep AI Service — OpenRouter (primary) or OpenAI (fallback).
Falls back to rich mock responses when no API key is configured or credits are exhausted.
"""
from __future__ import annotations
import json
from typing import Optional, List
from app.config import get_settings

settings = get_settings()

# ── Client factory ─────────────────────────────────────────────────────────────

def _get_client():
    """
    Returns (client, model_name) tuple.
    Priority: OpenRouter key > OpenAI key > None (mock mode).
    """
    try:
        from openai import OpenAI

        # 1. OpenRouter — preferred (has free models)
        if settings.openrouter_api_key:
            client = OpenAI(
                api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url,
                default_headers={
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "CloudPrep AI",
                },
            )
            return client, settings.openrouter_model

        # 2. Direct OpenAI fallback
        if settings.openai_api_key:
            client = OpenAI(api_key=settings.openai_api_key)
            return client, settings.openai_model

    except Exception:
        pass

    return None, None


def _is_quota_error(e: Exception) -> bool:
    """True for billing / quota errors — we fall back to mocks silently."""
    msg = str(e).lower()
    return any(k in msg for k in [
        "credit", "quota", "billing", "insufficient_quota",
        "credit_balance_exhausted", "rate_limit", "429",
    ])


# ── System prompts ────────────────────────────────────────────────────────────

MENTOR_SYSTEM = """You are CloudPrep AI — an expert cloud engineering mentor specialising in:
Linux, AWS, Docker, Kubernetes, Terraform, CI/CD, Networking, and Cloud Security.

Your style:
- Clear, concise, practical explanations with real-world examples.
- Use code snippets when helpful (wrap in markdown fences).
- If asked an interview question, explain the concept AND give a model answer.
- Always end with a follow-up suggestion or a quick quiz question to reinforce learning.
- Be encouraging but technically rigorous.
"""

INTERVIEWER_SYSTEM = """You are an experienced cloud infrastructure interviewer at a top tech company.
Generate ONE specific, scenario-based interview question at the specified difficulty level.
Return ONLY a JSON object: { "question": "...", "expected_keywords": ["kw1", "kw2", ...] }
No extra text outside the JSON.
"""

SCORER_SYSTEM = """You are evaluating a candidate's answer to a cloud engineering interview question.
Return ONLY a JSON object:
{
  "score": <0-100 integer>,
  "strengths": ["..."],
  "improvements": ["..."],
  "model_answer": "A 2-3 sentence ideal answer."
}
Score 90-100 = excellent, 70-89 = good, 50-69 = partial, <50 = needs work.
No extra text outside the JSON.
"""


# ── Mentor Chat ───────────────────────────────────────────────────────────────

def mentor_reply(
    message: str,
    history: List[dict],
    topic_context: Optional[str] = None,
) -> str:
    """Return an AI mentor reply. Falls back to rich mocks when AI is unavailable."""
    client, model = _get_client()

    if not client:
        return _mock_mentor_reply(message, topic_context)

    messages = [{"role": "system", "content": MENTOR_SYSTEM}]
    if topic_context:
        messages.append({"role": "system", "content": f"Current topic context: {topic_context}"})
    messages.extend(history[-10:])
    messages.append({"role": "user", "content": message})

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=800,
        )
        return resp.choices[0].message.content or "I couldn't generate a response. Please try again."
    except Exception as e:
        if _is_quota_error(e):
            # Silently fall back to mocks — don't expose billing errors to users
            return _mock_mentor_reply(message, topic_context)
        return f"⚠️ Something went wrong: {e}"


def _mock_mentor_reply(message: str, topic: Optional[str]) -> str:
    msg_lower = message.lower()
    if any(k in msg_lower for k in ["docker", "container"]):
        return (
            "**Docker** packages your app and its dependencies into a portable container image.\n\n"
            "```bash\n# Build an image\ndocker build -t myapp:latest .\n\n# Run a container\ndocker run -d -p 8080:80 myapp:latest\n```\n\n"
            "💡 **Key concepts**: Dockerfile → Image → Container → Registry.\n\n"
            "**Follow-up**: What's the difference between `CMD` and `ENTRYPOINT` in a Dockerfile?"
        )
    if any(k in msg_lower for k in ["kubernetes", "k8s", "pod"]):
        return (
            "**Kubernetes** is an orchestration system for containers.\n\n"
            "Core objects: **Pod** (smallest unit) → **Deployment** (manages Pods) → **Service** (exposes Pods) → **Ingress** (HTTP routing).\n\n"
            "```yaml\napiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: my-app\nspec:\n  replicas: 3\n  selector:\n    matchLabels:\n      app: my-app\n  template:\n    metadata:\n      labels:\n        app: my-app\n    spec:\n      containers:\n      - name: app\n        image: my-app:latest\n        ports:\n        - containerPort: 80\n```\n\n"
            "**Follow-up**: What happens when a Pod crashes in a Deployment?"
        )
    if any(k in msg_lower for k in ["aws", "ec2", "s3", "lambda"]):
        return (
            "**AWS** core services to know as a Cloud Engineer:\n\n"
            "| Service | Purpose |\n|---|---|\n| EC2 | Virtual machines |\n| S3 | Object storage |\n| RDS | Managed databases |\n| Lambda | Serverless functions |\n| VPC | Private networking |\n| IAM | Identity & access management |\n\n"
            "**Follow-up**: Can you explain the difference between a Security Group and a NACL in VPC?"
        )
    return (
        f"Great question{' about ' + topic if topic else ''}! 🎯\n\n"
        "To get **AI-powered answers**, add your `OPENAI_API_KEY` to `backend/.env`.\n\n"
        "In the meantime, here are the top resources to explore:\n"
        "- 📖 [AWS Documentation](https://docs.aws.amazon.com)\n"
        "- 🎓 [Linux Foundation Training](https://training.linuxfoundation.org)\n"
        "- 🐳 [Docker Official Docs](https://docs.docker.com)\n"
        "- ☸️ [Kubernetes Docs](https://kubernetes.io/docs)\n\n"
        "**Follow-up**: Which specific cloud topic would you like to deep-dive into today?"
    )


# ── Interview Question Generator ──────────────────────────────────────────────

def generate_interview_question(topic: Optional[str], difficulty: str) -> dict:
    """Returns { question, expected_keywords }."""
    client, model = _get_client()
    if not client:
        return _mock_question(topic, difficulty)

    topic_str = f" specifically on '{topic}'" if topic else " on software engineering & architecture"
    prompt = (
        f"Generate a {difficulty}-level technical interview question{topic_str}.\n"
        f"Return ONLY a JSON object: {{ \"question\": \"...\", \"expected_keywords\": [\"kw1\", \"kw2\", ...] }}"
    )

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a senior technical interviewer at a top company. Return ONLY valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
            max_tokens=350,
        )
        raw = resp.choices[0].message.content or "{}"
        raw = raw.strip().strip("```json").strip("```").strip()
        data = json.loads(raw)
        return {
            "question": data.get("question", f"Explain the core architectural principles of {topic or 'modern software systems'}."),
            "expected_keywords": data.get("expected_keywords", []),
        }
    except Exception as e:
        return _mock_question(topic, difficulty)


def _mock_question(topic: Optional[str], difficulty: str) -> dict:
    if topic:
        t_low = topic.lower()
        if "front" in t_low or "react" in t_low or "javascript" in t_low or "ui" in t_low:
            return {
                "question": f"Explain the Virtual DOM and reconciliation process in React. How does it optimize rendering performance compared to direct DOM updates?",
                "expected_keywords": ["Virtual DOM", "diffing", "reconciliation", "fiber", "state update"],
            }
        if "back" in t_low or "node" in t_low or "api" in t_low or "python" in t_low:
            return {
                "question": f"How do you design a secure, idempotent REST API in {topic}? Explain handling auth, token expiry, and database race conditions.",
                "expected_keywords": ["idempotency", "JWT", "middleware", "transactions", "locking"],
            }
        if "data" in t_low or "sql" in t_low or "postgres" in t_low or "mongo" in t_low:
            return {
                "question": f"Compare SQL vs NoSQL for high-concurrency systems. When would you choose one over the other in {topic}?",
                "expected_keywords": ["ACID", "indexes", "sharding", "consistency", "CAP theorem"],
            }
        return {
            "question": f"In {topic}, what are the most critical architectural patterns and best practices for building scalable, maintainable production systems?",
            "expected_keywords": ["architecture", "modularity", "scalability", "testing", "monitoring"],
        }

    bank = {
        "easy": {
            "question": "What is the difference between a process and a thread, and how does memory sharing work?",
            "expected_keywords": ["process", "thread", "memory", "context switch", "stack"],
        },
        "medium": {
            "question": "Explain how modern microservices handle distributed data consistency and service-to-service authentication.",
            "expected_keywords": ["JWT", "API gateway", "Saga pattern", "eventual consistency", "mTLS"],
        },
        "hard": {
            "question": "Design a highly available, multi-region distributed system that handles 100k requests/second with low latency. Walk through your architecture, caching, and failover strategy.",
            "expected_keywords": ["load balancer", "caching", "Redis", "replication", "partitioning", "failover"],
        },
    }
    return bank.get(difficulty, bank["medium"])


# ── Interview Answer Scorer ───────────────────────────────────────────────────

def score_interview_answer(question: str, answer: str, topic: Optional[str]) -> dict:
    """Returns { score, strengths, improvements, model_answer }."""
    client, model = _get_client()
    if not client:
        return _mock_score(answer)

    prompt = (
        f"Question: {question}\n\nCandidate answer: {answer}"
        + (f"\n\nTopic area: {topic}" if topic else "")
    )

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SCORER_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=600,
        )
        raw = resp.choices[0].message.content or "{}"
        raw = raw.strip().strip("```json").strip("```").strip()
        data = json.loads(raw)
        return {
            "score": int(data.get("score", 60)),
            "strengths": data.get("strengths", []),
            "improvements": data.get("improvements", []),
            "model_answer": data.get("model_answer", ""),
        }
    except Exception:
        return _mock_score(answer)


def _mock_score(answer: str) -> dict:
    word_count = len(answer.split())
    score = min(85, max(40, 50 + word_count // 3))
    return {
        "score": score,
        "strengths": ["Shows foundational understanding", "Clear communication"],
        "improvements": [
            "Add specific examples or commands",
            "Mention trade-offs or edge cases",
        ],
        "model_answer": (
            "Configure your OPENAI_API_KEY in backend/.env to receive "
            "a detailed model answer tailored to this specific question."
        ),
    }


# ── XP Calculation ─────────────────────────────────────────────────────────────

def calc_session_xp(duration_minutes: int) -> int:
    """XP for a study session: 1 XP per minute, bonus tiers."""
    base = duration_minutes
    if duration_minutes >= 120:
        return int(base * 1.5)
    if duration_minutes >= 60:
        return int(base * 1.25)
    return base


def calc_interview_xp(score: int) -> int:
    """XP for completing a mock interview based on score."""
    if score >= 90:
        return 50
    if score >= 70:
        return 35
    if score >= 50:
        return 20
    return 10


# ── Level system ───────────────────────────────────────────────────────────────

LEVELS = [
    (0,     "Novice Explorer",      "🌱"),
    (200,   "Foundation Builder",   "🧱"),
    (500,   "Skill Practitioner",   "⚡"),
    (1000,  "Core Specialist",      "🎯"),
    (2000,  "Advanced Developer",   "🚀"),
    (3500,  "Lead Architect",       "🛡️"),
    (5000,  "Principal Engineer",   "🏛️"),
    (8000,  "Distinguished Master", "🔭"),
    (12000, "Grandmaster Champion", "👑"),
]


def get_level_info(total_xp: int) -> dict:
    level_num = 1
    level_name = LEVELS[0][1]
    xp_to_next = LEVELS[1][0]

    for i, (threshold, name, _) in enumerate(LEVELS):
        if total_xp >= threshold:
            level_num = i + 1
            level_name = name
            if i + 1 < len(LEVELS):
                xp_to_next = LEVELS[i + 1][0] - total_xp
            else:
                xp_to_next = 0

    return {"level": level_num, "level_name": level_name, "xp_to_next": max(0, xp_to_next)}


# ── Streak calculation ─────────────────────────────────────────────────────────

def calc_streak(session_dates: list[str]) -> tuple[int, int]:
    """
    Given sorted list of 'YYYY-MM-DD' strings, return (current_streak, longest_streak).
    """
    from datetime import date, timedelta

    if not session_dates:
        return 0, 0

    unique_dates = sorted(set(session_dates), reverse=True)
    today = date.today()

    # Check if streak is still alive (studied today or yesterday)
    last = date.fromisoformat(unique_dates[0])
    if (today - last).days > 1:
        current_streak = 0
    else:
        current_streak = 1
        for i in range(1, len(unique_dates)):
            prev = date.fromisoformat(unique_dates[i])
            curr = date.fromisoformat(unique_dates[i - 1])
            if (curr - prev).days == 1:
                current_streak += 1
            else:
                break

    # Longest streak
    longest = 1
    run = 1
    for i in range(1, len(unique_dates)):
        prev = date.fromisoformat(unique_dates[i])
        curr = date.fromisoformat(unique_dates[i - 1])
        if (curr - prev).days == 1:
            run += 1
            longest = max(longest, run)
        else:
            run = 1

    return current_streak, longest


# ── Full AI Course Generation ──────────────────────────────────────────────────

def generate_course_questions(topic: str, duration_days: int = 30) -> list[dict]:
    """
    Generate 3-4 interactive clarifying questions for the user before building the full course.
    """
    client, model = _get_client()

    default_questions = [
        {
            "id": "level",
            "question": f"What is your current experience level with {topic}?",
            "options": [
                "Complete Beginner (Starting from scratch)",
                "Intermediate (Know the basics, want depth & best practices)",
                "Advanced (Targeting senior-level mastery & architectures)",
            ],
            "default": "Intermediate (Know the basics, want depth & best practices)",
        },
        {
            "id": "stack",
            "question": f"What specific tech stack or specialization do you want to emphasize for {topic}?",
            "options": [
                "Most popular & modern industry standard tools",
                "Hands-on project & practical real-world focus",
                "Interview preparation & theoretical foundations",
                "Fast-track core fundamentals only",
            ],
            "default": "Hands-on project & practical real-world focus",
        },
        {
            "id": "goal",
            "question": "What is your ultimate goal upon completing this course?",
            "options": [
                "Land a high-paying job / transition careers",
                "Build & deploy a complete portfolio project / product",
                "Crack technical interviews & system design rounds",
                "Upskill for current work / promotion",
            ],
            "default": "Land a high-paying job / transition careers",
        },
        {
            "id": "pace",
            "question": "How many hours per day can you commit?",
            "options": [
                "1-2 hours/day (Casual & steady)",
                "2-3 hours/day (Standard recommended pace)",
                "4+ hours/day (Intensive bootcamp immersion)",
            ],
            "default": "2-3 hours/day (Standard recommended pace)",
        },
    ]

    if not client:
        return default_questions

    prompt = (
        f"A learner wants to create a {duration_days}-day course on '{topic}'.\n"
        f"Generate exactly 3 to 4 multiple-choice clarifying questions to customize this course for them.\n"
        f"Return ONLY valid JSON array formatted as:\n"
        f'[\n  {{"id": "q1", "question": "...", "options": ["opt1", "opt2", "opt3"], "default": "opt1"}}\n]'
    )

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a curriculum design expert. Return ONLY valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=700,
        )
        content = resp.choices[0].message.content or ""
        import re
        match = re.search(r'\[.*\]', content, re.DOTALL)
        if match:
            questions = json.loads(match.group())
            if isinstance(questions, list) and len(questions) >= 2:
                return questions
    except Exception:
        pass

    return default_questions


def generate_full_course(
    topic: str,
    duration_days: int = 30,
    answers: Optional[dict] = None,
    context: Optional[str] = None,
) -> dict:
    """
    Generate a complete day-by-day course curriculum for any topic and duration with docs and YouTube video links.
    """
    import urllib.parse
    client, model = _get_client()
    answers = answers or {}

    ans_str = ", ".join(f"{k}: {v}" for k, v in answers.items() if v)
    course_title = f"{topic}: {duration_days}-Day Comprehensive Track"

    if client:
        prompt = (
            f"Create a complete, detailed {duration_days}-day learning course for '{topic}'.\n"
            f"Learner details & preferences: {ans_str}. {context or ''}\n\n"
            f"Rules:\n"
            f"1. Generate exactly {duration_days} days numbered 1 to {duration_days}.\n"
            f"2. Each day must belong to a week number (week = ceil(day / 7)).\n"
            f"3. Include realistic, helpful 'domain' (module/subject area), 'topic', 'subtopic' (detailed concepts), "
            f"'lab' (concrete hands-on exercise), 'resource_url' (official docs/reading link), 'youtube_url' (YouTube tutorial/search URL), and 'planned_hours' (1-4).\n"
            f"4. Structure progression logically: Foundations -> Core Mechanisms -> Advanced Concepts -> Real Projects -> Interview/Portfolio Polish.\n"
            f"5. Return ONLY a valid JSON object with format:\n"
            f'{{\n  "course_name": "{topic} Masterclass",\n  "description": "...",\n  "days": [\n'
            f'    {{"day": 1, "week": 1, "domain": "Foundations", "topic": "...", "subtopic": "...", "lab": "...", "resource_url": "https://...", "youtube_url": "https://www.youtube.com/results?search_query=...", "planned_hours": 3}}\n'
            f'  ]\n}}'
        )

        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a world-class education curriculum architect. Output ONLY valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=4000,
            )
            content = resp.choices[0].message.content or ""
            import re
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                data = json.loads(match.group())
                days_list = data.get("days", [])
                if isinstance(days_list, list) and len(days_list) > 0:
                    # Validate / fix days indexing
                    formatted_days = []
                    for i, d in enumerate(days_list):
                        day_num = i + 1
                        week_num = (day_num - 1) // 7 + 1
                        day_topic = d.get("topic", f"{topic} Part {day_num}")
                        day_domain = d.get("domain", "Core")
                        yt_url = d.get("youtube_url")
                        if not yt_url:
                            yt_q = f"{day_domain} {day_topic} tutorial"
                            yt_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(yt_q)}"
                        formatted_days.append({
                            "day": day_num,
                            "week": week_num,
                            "domain": day_domain,
                            "topic": day_topic,
                            "subtopic": d.get("subtopic", "Concepts and fundamentals"),
                            "lab": d.get("lab", "Hands-on practice exercise"),
                            "resource_url": d.get("resource_url", "https://roadmap.sh"),
                            "youtube_url": yt_url,
                            "planned_hours": int(d.get("planned_hours", 3)),
                        })
                    return {
                        "course_name": data.get("course_name", course_title),
                        "description": data.get("description", f"A complete {duration_days}-day course on {topic}."),
                        "days": formatted_days,
                    }
        except Exception:
            pass

    # Algorithmic high-quality fallback generator
    return _algorithmic_course_generator(topic, duration_days, answers)


def _algorithmic_course_generator(topic: str, duration_days: int, answers: dict) -> dict:
    """Generates structured day-by-day curriculum with docs and YouTube tutorial links for any subject."""
    import math
    import urllib.parse

    topic_lower = topic.lower()
    total_weeks = math.ceil(duration_days / 7)

    # Domain stages
    if "fullstack" in topic_lower or "web" in topic_lower:
        modules = [
            ("Frontend Basics", "HTML5, modern CSS, semantic layouts, responsive design", "Build responsive landing page", "https://developer.mozilla.org"),
            ("JavaScript Deep Dive", "ES6+, async/await, closures, DOM manipulation, Fetch API", "Interactive browser dashboard", "https://javascript.info"),
            ("React & Modern UI", "Components, hooks, state management, routing, Tailwind", "Dynamic Single Page Application", "https://react.dev"),
            ("Backend & REST APIs", "Node.js/Express, REST architecture, middleware, validation", "RESTful API with authentication", "https://nodejs.org"),
            ("Database & ORM", "PostgreSQL/MongoDB, schema design, queries, Prisma/Mongoose", "Database integration & relations", "https://www.postgresql.org/docs/"),
            ("Fullstack Integration", "Connecting client & server, JWT auth, state sync", "Complete fullstack web app", "https://nextjs.org/docs"),
            ("Testing & CI/CD", "Unit tests, Jest, GitHub Actions, Dockerizing apps", "Automated deployment pipeline", "https://docs.github.com/actions"),
            ("Production & Scale", "Cloud deployment, caching (Redis), security, performance", "Production release with HTTPS", "https://roadmap.sh/full-stack"),
            ("Capstone Project", "End-to-end fullstack platform with real-world features", "Build & ship capstone product", "https://github.com"),
            ("Interview & Polish", "Fullstack system design, coding challenges, portfolio polish", "Mock technical interviews", "https://roadmap.sh"),
        ]
    elif "python" in topic_lower or "data science" in topic_lower or "ai" in topic_lower or "machine learning" in topic_lower:
        modules = [
            ("Python Core", "Data structures, functions, OOP, exceptions, file handling", "Build CLI data utility", "https://docs.python.org/3/"),
            ("NumPy & Pandas", "Array manipulation, DataFrame operations, cleaning, aggregation", "Clean & analyze real-world dataset", "https://pandas.pydata.org/"),
            ("Data Visualization", "Matplotlib, Seaborn, interactive plots, insight storytelling", "Visual dashboard report", "https://seaborn.pydata.org/"),
            ("Math & Stats Foundations", "Linear algebra, probability, hypothesis testing, metrics", "Statistical data exploration", "https://khanacademy.org"),
            ("Machine Learning Core", "Scikit-Learn, regression, classification, clustering, validation", "Train predictive ML model", "https://scikit-learn.org/"),
            ("Deep Learning & PyTorch", "Neural networks, backprop, PyTorch tensors, model training", "Train computer vision / NLP model", "https://pytorch.org/tutorials/"),
            ("LLMs & Modern AI", "Prompt engineering, embeddings, LangChain, vector DBs", "Build RAG chatbot application", "https://platform.openai.com/docs"),
            ("Model Deployment", "FastAPI, Docker containerization, cloud serving, Streamlit", "Deploy AI model as web service", "https://fastapi.tiangolo.com/"),
            ("Capstone AI Project", "Complete end-to-end machine learning / AI application", "End-to-end AI project build", "https://huggingface.co/"),
            ("Portfolio & Career", "Project documentation, GitHub showcases, AI interview prep", "Publish portfolio & review", "https://roadmap.sh/ai-data-scientist"),
        ]
    elif "mobile" in topic_lower or "flutter" in topic_lower or "react native" in topic_lower or "ios" in topic_lower or "android" in topic_lower:
        modules = [
            ("Mobile Foundations", "UI layouts, widgets, navigation, design guidelines", "Build basic mobile app screen", "https://flutter.dev"),
            ("State Management", "State lifecycles, reactive state, store patterns", "Interactive task management app", "https://reactnative.dev"),
            ("API & Local Storage", "HTTP requests, offline caching, SQLite/Hive, JSON parsing", "News reader app with offline mode", "https://developer.android.com"),
            ("Device Features", "Camera, GPS/Location, push notifications, permissions", "Location-aware mobile feature", "https://developer.apple.com"),
            ("App Architecture", "Clean architecture, dependency injection, reusable modules", "Refactor into modular architecture", "https://roadmap.sh"),
            ("Testing & Release", "Unit tests, widget tests, CI/CD for mobile, App Store/Play Store", "Prepare production release bundle", "https://fastlane.tools/"),
            ("Capstone Mobile App", "Full feature mobile app with backend integration", "Complete mobile product build", "https://github.com"),
            ("Portfolio & Career", "App demo recordings, resume showcase, mobile interview prep", "Publish app & portfolio", "https://roadmap.sh"),
        ]
    else:
        # Generalized curriculum
        modules = [
            ("Core Foundations", f"Essential concepts, mental models, environment setup in {topic}", "Setup environment and first project", "https://roadmap.sh"),
            ("Fundamental Tools", f"Key building blocks, syntax, and essential workflows for {topic}", "Hands-on foundation exercise", "https://google.com"),
            ("Intermediate Mastery", f"Best practices, patterns, error handling, and techniques in {topic}", "Build intermediate component", "https://roadmap.sh"),
            ("Advanced Architecture", f"Complex scenarios, optimization, scalability, and deep dive in {topic}", "Optimize & scale practical solution", "https://github.com"),
            ("Practical Project", f"Real-world hands-on project applying all {topic} principles", "Build end-to-end project", "https://roadmap.sh"),
            ("System Design & Best Practices", f"Architecture patterns, industry standards, security in {topic}", "Design real-world architecture", "https://github.com"),
            ("Portfolio & Interview Prep", f"Top interview questions, portfolio documentation, and review for {topic}", "Document and showcase portfolio", "https://roadmap.sh"),
        ]

    days = []
    num_modules = len(modules)

    for i in range(duration_days):
        day_num = i + 1
        week_num = (day_num - 1) // 7 + 1
        mod_idx = int((i / duration_days) * num_modules)
        mod_idx = min(mod_idx, num_modules - 1)
        mod_name, mod_subtopic, mod_lab, mod_url = modules[mod_idx]

        day_in_mod = (i % max(1, math.ceil(duration_days / num_modules))) + 1
        topic_title = f"{mod_name}: Part {day_in_mod}" if duration_days > 14 else f"{mod_name} Essentials"
        yt_query = f"{topic} {mod_name} {topic_title} tutorial"
        yt_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(yt_query)}"

        days.append({
            "day": day_num,
            "week": week_num,
            "domain": mod_name,
            "topic": topic_title,
            "subtopic": f"{mod_subtopic} (Day {day_num} milestones and focus areas)",
            "lab": f"{mod_lab} — Step {day_in_mod}",
            "resource_url": mod_url,
            "youtube_url": yt_url,
            "planned_hours": 3,
        })

    return {
        "course_name": f"{topic} Master Track",
        "description": f"A comprehensive {duration_days}-day structured path designed to take you from foundational understanding to full practical confidence in {topic}.",
        "days": days,
    }

