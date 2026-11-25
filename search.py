"""Live web search through Tavily (free plan: 1,000 searches a month, no card)."""
from __future__ import annotations

import requests

import config as C
from rules import platform_for

TAVILY_URL = "https://api.tavily.com/search"
SNIPPET_CHARS = 500


class SearchError(Exception):
    pass


def _one_search(api_key: str, step: dict, company: str, role: str) -> list[dict]:
    body = {
        "query": step["query"].format(company=company, role=role or "").strip(),
        "search_depth": "basic",  # 1 credit
        "max_results": 5,
        "topic": step.get("topic", "general"),
    }
    if step.get("include_domains"):
        body["include_domains"] = step["include_domains"]
        if step.get("include_domains_mode"):
            body["include_domains_mode"] = step["include_domains_mode"]
    if step.get("time_range"):
        body["time_range"] = step["time_range"]

    resp = requests.post(
        TAVILY_URL,
        json=body,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
    )
    if resp.status_code == 401:
        raise SearchError("The Tavily key was rejected. Check TAVILY_API_KEY in the app settings.")
    if resp.status_code in (432, 433):
        raise SearchError("This month's free Tavily searches are used up. They reset next month.")
    if resp.status_code == 429:
        raise SearchError("Tavily is rate-limiting requests. Wait a minute and run it again.")
    resp.raise_for_status()

    out = []
    for r in resp.json().get("results", []):
        url = r.get("url") or ""
        if not url:
            continue
        out.append(
            {
                "title": (r.get("title") or url)[:200],
                "url": url,
                "snippet": " ".join((r.get("content") or "").split())[:SNIPPET_CHARS],
                "platform": platform_for(url, step.get("topic", "general")),
                "found_by": step["key"],
                "published": r.get("published_date") or "",
            }
        )
    return out


def run_searches(api_key: str, company: str, role: str, on_step=None) -> tuple[list[dict], list[str]]:
    """Run every search in config.SEARCH_PLAN. Returns (sources, warnings)."""
    sources: list[dict] = []
    seen: set[str] = set()
    warnings: list[str] = []
    for step in C.SEARCH_PLAN:
        if on_step:
            on_step(step["label"])
        results = None
        for attempt in range(2):  # one retry for a network hiccup
            try:
                results = _one_search(api_key, step, company, role)
                break
            except SearchError:
                raise
            except Exception as e:  # one failed search shouldn't stop the whole run
                if attempt == 1:
                    warnings.append(f"{step['label']}: search failed twice ({type(e).__name__}), skipped.")
        if results is None:
            continue
        for s in results:
            if s["url"] in seen:
                continue
            seen.add(s["url"])
            sources.append(s)
    return sources, warnings
