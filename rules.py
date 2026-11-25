"""Fixed rules: tiers, scores, verdicts and source counting. No AI in here."""
from __future__ import annotations

import re
from urllib.parse import urlparse

from . import config as C


# ---------------------------------------------------------------- helpers
def company_key(name: str) -> str:
    """Normalise a company name so 'Deloitte India Pvt. Ltd.' == 'deloitte india'."""
    s = (name or "").lower()
    s = re.sub(r"[^a-z0-9& ]+", " ", s)
    s = re.sub(r"\b(private|pvt|limited|ltd|llp|inc|incorporated|corp|corporation|co|company)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def platform_for(url: str, topic: str = "general") -> str:
    host = (urlparse(url or "").hostname or "").lower()
    host = host[4:] if host.startswith("www.") else host
    for domain, label in C.PLATFORMS.items():
        if host == domain or host.endswith("." + domain):
            return label
    return "News" if topic == "news" else "Web"


def domain_of(url: str) -> str:
    host = (urlparse(url or "").hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


# ---------------------------------------------------------------- tiers
def tier_for_ctc(ctc_lpa: float) -> int:
    if ctc_lpa >= C.TIER_1_MIN:
        return 1
    if ctc_lpa >= C.TIER_2_MIN:
        return 2
    return 3


def final_tier(base_tier: int, override: bool) -> int:
    """An exceptional brand or role moves the offer up one tier (CMC decides)."""
    return max(1, base_tier - 1) if override else base_tier


# ---------------------------------------------------------------- scores
def package_score(ctc_lpa: float) -> float:
    pts = C.PACKAGE_CURVE
    if ctc_lpa <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if ctc_lpa <= x1:
            return round(y0 + (y1 - y0) * (ctc_lpa - x0) / (x1 - x0), 1)
    return pts[-1][1]


def clamp_score(v, default: float = 5.0) -> float:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return default
    return round(min(10.0, max(0.0, v)), 1)


def total_score(scores: dict) -> float:
    return round(sum(C.WEIGHTS[k] * scores[k] for k in C.WEIGHTS), 1)


def verdict_for(score: float) -> str:
    if score >= C.RECOMMEND_MIN:
        return "Recommend"
    if score >= C.CAUTION_MIN:
        return "Go with caution"
    return "Avoid"


def apply_red_flag_cap(verdict: str, red_flags: list[dict]) -> tuple[str, str | None]:
    """Serious red flags confirmed by enough sources cap the verdict at caution."""
    if verdict != "Recommend":
        return verdict, None
    for f in red_flags:
        if f.get("severity") == "high" and (
            f.get("confirmed") or f.get("source_count", 0) >= C.RED_FLAG_CAP_SOURCES
        ):
            return "Go with caution", f.get("flag")
    return verdict, None


def bond_flag(bond_months: int) -> dict | None:
    if not bond_months:
        return None
    if bond_months >= C.BOND_SERIOUS_MONTHS:
        sev = "high"
    elif bond_months >= C.BOND_NOTABLE_MONTHS:
        sev = "medium"
    else:
        sev = "low"
    return {
        "flag": f"Service bond of {bond_months} months (entered by CMC)",
        "severity": sev,
        "source_ids": [],
        "source_count": 0,
        "confirmed": True,
    }


# ---------------------------------------------------------------- consensus
REVIEW_PLATFORMS = {"Reddit", "AmbitionBox", "Glassdoor", "Indeed", "Naukri", "LinkedIn"}


def origin_of(s: dict) -> str:
    """Review sites count as one origin each; every news outlet or website counts separately."""
    return s["platform"] if s.get("platform") in REVIEW_PLATFORMS else (domain_of(s.get("url", "")) or s.get("platform", "Web"))


def consensus_label(source_ids: list[int], sources: list[dict]) -> dict:
    """How many independent sources say this? Counted in code, not by the AI."""
    picked = [sources[i] for i in source_ids if 0 <= i < len(sources)]
    urls = {s["url"] for s in picked}
    platforms = {origin_of(s) for s in picked}
    n = len(urls)
    if n >= C.WIDELY_REPORTED_MIN_SOURCES and len(platforms) >= 2:
        label, level = "Widely reported", "wide"
    elif n >= C.REPEATED_MIN_SOURCES:
        label, level = "Repeated", "repeated"
    elif n == 1:
        label, level = "Single mention", "single"
    else:
        label, level = "No source", "none"
    return {"label": label, "level": level, "sources": n, "platforms": sorted(platforms)}


def clean_ids(ids, n_sources: int) -> list[int]:
    out = []
    for i in ids or []:
        try:
            i = int(i)
        except (TypeError, ValueError):
            continue
        if 0 <= i < n_sources and i not in out:
            out.append(i)
    return out
