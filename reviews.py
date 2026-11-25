"""Checks that keep student reviews honest."""
from __future__ import annotations

import difflib
import hashlib
import re
from datetime import datetime, timedelta, timezone

from . import config as C

RATING_FIELDS = {
    "rating_overall": "Overall",
    "rating_wlb": "Work-life balance",
    "rating_culture": "Culture",
    "rating_growth": "Learning and growth",
    "rating_management": "Managers",
}

AI_MATCH = {
    "matches": ("Matches outside sources", 0),
    "partly": ("Partly matches outside sources", -10),
    "contradicts": ("Contradicts outside sources", -35),
    "unverifiable": ("Can't be checked yet", -10),
}

FLAG_TEXT = {
    "too_short": "Very little detail",
    "extreme_ratings": "Every rating is the same extreme",
    "near_duplicate": "Almost the same text as another review",
    "burst": "Part of a sudden burst of reviews",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_iso(s: str) -> datetime:
    try:
        d = datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


def valid_fiib_email(email: str) -> bool:
    pattern = r"^[A-Za-z0-9._%+\-]+@" + re.escape(C.FIIB_EMAIL_DOMAIN) + r"$"
    return bool(re.match(pattern, (email or "").strip(), flags=re.IGNORECASE))


def hash_email(email: str, salt: str) -> str:
    return hashlib.sha256((salt + email.strip().lower()).encode()).hexdigest()[:24]


def review_text(r: dict) -> str:
    return " ".join(str(r.get(k, "")) for k in ("pros", "cons", "interview")).strip()


def heuristic_flags(new: dict, existing_same_company: list[dict]) -> list[str]:
    flags = []
    text = review_text(new)
    if len(text) < C.MIN_REVIEW_CHARS:
        flags.append("too_short")

    ratings = [int(new.get(k) or 0) for k in RATING_FIELDS]
    if ratings and (all(v == 1 for v in ratings) or all(v == 5 for v in ratings)):
        flags.append("extreme_ratings")

    low = text.lower()
    for r in existing_same_company:
        other = review_text(r).lower()
        if other and low and difflib.SequenceMatcher(None, low, other).ratio() >= C.NEAR_DUPLICATE_RATIO:
            flags.append("near_duplicate")
            break

    cutoff = datetime.now(timezone.utc) - timedelta(hours=C.BURST_WINDOW_HOURS)
    recent = [r for r in existing_same_company if parse_iso(r.get("created_at", "")) >= cutoff]
    if len(recent) + 1 >= C.BURST_MIN_REVIEWS:
        flags.append("burst")
    return flags


def credibility(review: dict) -> dict:
    score = 100
    flags = review.get("flags") or []
    score -= 25 * len(flags)
    match = review.get("ai_match")
    if match in AI_MATCH:
        score += AI_MATCH[match][1]
    score = max(0, min(100, score))
    if score >= 75:
        label, level = "High credibility", "high"
    elif score >= 50:
        label, level = "Medium credibility", "medium"
    else:
        label, level = "Low credibility", "low"
    return {"score": score, "label": label, "level": level}
