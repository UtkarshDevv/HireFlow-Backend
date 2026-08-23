"""
Job Aggregator Service
──────────────────────
Fetches jobs from legitimate public APIs:
  - Adzuna (free tier, 250 req/day) — requires APP_ID + APP_KEY
  - RemoteOK (no key needed, JSON feed)
  - USAJobs (free government API)

All sources normalize to the same job dict shape.
"""
import httpx
from app.config import get_settings

settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# Main dispatch
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_jobs(
    query: str,
    location: str = "remote",
    sources: list[str] = None,
    max_results: int = 20,
) -> list[dict]:
    """Fetch from all requested sources and return normalized job dicts."""
    if sources is None:
        sources = ["adzuna", "remoteok"]

    results = []
    per_source = max(1, max_results // len(sources))

    async with httpx.AsyncClient(timeout=15) as client:
        for source in sources:
            try:
                if source == "adzuna" and settings.adzuna_app_id:
                    jobs = await _fetch_adzuna(client, query, location, per_source)
                elif source == "remoteok":
                    jobs = await _fetch_remoteok(client, query, per_source)
                elif source == "usajobs":
                    jobs = await _fetch_usajobs(client, query, per_source)
                else:
                    continue
                results.extend(jobs)
            except Exception as e:
                print(f"[job_aggregator] Error fetching from {source}: {e}")

    return results[:max_results]


# ─────────────────────────────────────────────────────────────────────────────
# Source adapters
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_adzuna(client: httpx.AsyncClient, query: str, location: str, limit: int) -> list[dict]:
    country = "us"
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
    params = {
        "app_id": settings.adzuna_app_id,
        "app_key": settings.adzuna_app_key,
        "what": query,
        "where": location,
        "results_per_page": min(limit, 50),
        "content-type": "application/json",
    }
    resp = await client.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for item in data.get("results", []):
        jobs.append({
            "source": "adzuna",
            "source_url": item.get("redirect_url", ""),
            "company": item.get("company", {}).get("display_name", "Unknown"),
            "title": item.get("title", ""),
            "location": item.get("location", {}).get("display_name", ""),
            "description_raw": item.get("description", ""),
        })
    return jobs


async def _fetch_remoteok(client: httpx.AsyncClient, query: str, limit: int) -> list[dict]:
    url = "https://remoteok.com/api"
    headers = {"User-Agent": "AIJobApplied/1.0"}
    resp = await client.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    query_lower = query.lower()
    jobs = []
    for item in data:
        if not isinstance(item, dict) or "id" not in item:
            continue
        title = item.get("position", "")
        tags = " ".join(item.get("tags", []))
        if query_lower not in title.lower() and query_lower not in tags.lower():
            continue
        jobs.append({
            "source": "remoteok",
            "source_url": item.get("url", ""),
            "company": item.get("company", "Unknown"),
            "title": title,
            "location": "Remote",
            "description_raw": item.get("description", ""),
        })
        if len(jobs) >= limit:
            break
    return jobs


async def _fetch_usajobs(client: httpx.AsyncClient, query: str, limit: int) -> list[dict]:
    url = "https://data.usajobs.gov/api/search"
    headers = {
        "Authorization-Key": "",  # USAJobs works without key for basic requests
        "User-Agent": "ai-job-applied@example.com",
        "Host": "data.usajobs.gov",
    }
    params = {
        "Keyword": query,
        "ResultsPerPage": min(limit, 25),
        "Fields": "Min",
    }
    resp = await client.get(url, headers=headers, params=params)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for item in data.get("SearchResult", {}).get("SearchResultItems", []):
        mv = item.get("MatchedObjectDescriptor", {})
        jobs.append({
            "source": "usajobs",
            "source_url": mv.get("ApplyURI", [""])[0] if mv.get("ApplyURI") else "",
            "company": mv.get("OrganizationName", "U.S. Government"),
            "title": mv.get("PositionTitle", ""),
            "location": ", ".join(
                [loc.get("LocationName", "") for loc in mv.get("PositionLocation", [])]
            ),
            "description_raw": mv.get("UserArea", {}).get("Details", {}).get("JobSummary", ""),
        })
    return jobs
