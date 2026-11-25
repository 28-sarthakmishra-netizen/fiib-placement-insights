"""Runs one full assessment: tier -> web search -> AI reading -> counting -> score -> save."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import ai, config as C, rules
from .reviews import now_iso, parse_iso
from .search import run_searches
from .storage import new_id


def latest_for(assessments: list[dict], key: str) -> dict | None:
    same = [a for a in assessments if a.get("company_key") == key]
    return max(same, key=lambda a: a.get("created_at", "")) if same else None


def build_record(inp: dict, sources: list[dict], findings: dict, reviews: list[dict],
                 model: str, warnings: list[str]) -> dict:
    """Turn the AI's findings into a scored assessment. Pure function (easy to test)."""
    n = len(sources)
    ctc = float(inp["ctc_lpa"])
    base = rules.tier_for_ctc(ctc)
    tier = rules.final_tier(base, bool(inp.get("override")))

    # Claims: the code counts sources, not the AI.
    review_ids = {r["id"] for r in reviews}
    claims = []
    for c in findings.get("claims", []) or []:
        ids = rules.clean_ids(c.get("source_ids"), n)
        fiib = [i for i in (c.get("fiib_review_ids") or []) if i in review_ids]
        if not ids and not fiib:
            continue  # unsupported claims are dropped
        claims.append({
            "topic": c.get("topic", "Other"),
            "statement": str(c.get("statement", "")).strip(),
            "sentiment": c.get("sentiment", "mixed"),
            "source_ids": ids,
            "fiib_review_ids": fiib,
            "consensus": rules.consensus_label(ids, sources),
        })
    order = {"wide": 0, "repeated": 1, "single": 2, "none": 3}
    claims.sort(key=lambda c: (order[c["consensus"]["level"]], -c["consensus"]["sources"]))

    red_flags = []
    for f in findings.get("red_flags", []) or []:
        ids = rules.clean_ids(f.get("source_ids"), n)
        if not ids:
            continue
        cons = rules.consensus_label(ids, sources)
        red_flags.append({
            "flag": str(f.get("flag", "")).strip(),
            "severity": f.get("severity", "medium"),
            "source_ids": ids,
            "source_count": cons["sources"],
            "consensus": cons,
            "confirmed": False,
        })
    bond = rules.bond_flag(int(inp.get("bond_months") or 0))
    if bond:
        red_flags.insert(0, bond)

    ratings = []
    for r in findings.get("external_ratings", []) or []:
        ids = rules.clean_ids(r.get("source_ids"), n)
        if not ids:
            continue
        try:
            ratings.append({
                "platform": str(r.get("platform", "")),
                "rating": round(float(r.get("rating")), 1),
                "out_of": float(r.get("out_of") or 5),
                "based_on": str(r.get("based_on", "") or ""),
                "source_ids": ids,
            })
        except (TypeError, ValueError):
            continue

    scores = {
        "package": rules.package_score(ctc),
        "brand": rules.clamp_score((findings.get("brand") or {}).get("score")),
        "role": rules.clamp_score((findings.get("role") or {}).get("score")),
        "environment": rules.clamp_score((findings.get("environment") or {}).get("score")),
    }
    score = rules.total_score(scores)
    verdict, capped_by = rules.apply_red_flag_cap(rules.verdict_for(score), red_flags)

    checks = []
    for ch in findings.get("fiib_review_checks", []) or []:
        if ch.get("review_id") in review_ids:
            checks.append({"review_id": ch["review_id"], "match": ch.get("match", "unverifiable"),
                           "note": str(ch.get("note", ""))})

    exceptional = findings.get("exceptional") or {}
    return {
        "id": new_id("A"),
        "created_at": now_iso(),
        "company": inp["company"].strip(),
        "company_key": rules.company_key(inp["company"]),
        "role": inp["role"].strip(),
        "ctc_lpa": ctc,
        "location": (inp.get("location") or "").strip(),
        "bond_months": int(inp.get("bond_months") or 0),
        "base_tier": base,
        "tier": tier,
        "override": bool(inp.get("override")),
        "override_reason": (inp.get("override_reason") or "").strip(),
        "scores": scores,
        "score": score,
        "verdict": verdict,
        "verdict_capped_by": capped_by or "",
        "snapshot": str(findings.get("company_snapshot", "")),
        "summary": str(findings.get("summary", "")),
        "brand_reason": str((findings.get("brand") or {}).get("reason", "")),
        "role_reason": str((findings.get("role") or {}).get("reason", "")),
        "role_type": str((findings.get("role") or {}).get("role_type", "unclear")),
        "environment_reason": str((findings.get("environment") or {}).get("reason", "")),
        "external_ratings": ratings,
        "claims": claims,
        "red_flags": red_flags,
        "sources": sources,
        "review_checks": checks,
        "evidence_quality": findings.get("evidence_quality", "thin") if n else "thin",
        "ai_suggests_exceptional": bool(exceptional.get("suggest")),
        "ai_exceptional_reason": str(exceptional.get("reason", "")),
        "model": model,
        "warnings": warnings,
        "assessed_by": (inp.get("assessed_by") or "").strip(),
        "demo": False,
    }


def run_assessment(inp: dict, store, gemini_key: str, tavily_key: str,
                   gemini_model: str | None = None, on_step=None) -> dict:
    step = on_step or (lambda *_: None)
    key = rules.company_key(inp["company"])

    # 1. Sources: reuse recent ones for the same company unless a fresh search is asked for.
    assessments = store.list("assessments")
    prev = latest_for(assessments, key)
    fresh_cutoff = datetime.now(timezone.utc) - timedelta(days=C.SEARCH_CACHE_DAYS)
    if prev and not inp.get("fresh_search") and parse_iso(prev["created_at"]) >= fresh_cutoff \
            and prev.get("sources") and not prev.get("demo"):
        step("search", "Using sources saved on " + prev["created_at"][:10])
        sources, warnings = prev["sources"], ["Reused saved search results (saves free credits)."]
    else:
        sources, warnings = run_searches(
            tavily_key, inp["company"], inp["role"], on_step=lambda label: step("search", label)
        )

    # 2. FIIB reviews for this company (hidden ones are left out).
    reviews = [r for r in store.list("reviews") if r.get("company_key") == key and not r.get("hidden")]

    # 3. AI reading.
    step("ai", f"Reading {len(sources)} sources and {len(reviews)} FIIB reviews")
    prompt = ai.build_prompt(inp["company"], inp["role"], float(inp["ctc_lpa"]),
                             inp.get("location"), int(inp.get("bond_months") or 0), sources, reviews)
    findings, model = ai.analyse(gemini_key, prompt, gemini_model)

    # 4. Score, count and save.
    step("score", "Counting sources and scoring")
    rec = build_record(inp, sources, findings, reviews, model, warnings)
    store.add("assessments", rec)
    for ch in rec["review_checks"]:
        store.update("reviews", ch["review_id"], {"ai_match": ch["match"], "ai_note": ch["note"]})
    step("done", "Saved")
    return rec
