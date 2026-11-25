"""Run with:  python -m pytest -q"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ai, pipeline, rules, search, storage  # noqa: E402
from reviews import credibility, hash_email, heuristic_flags, valid_fiib_email  # noqa: E402
import components as ui  # noqa: E402


# ------------------------------------------------------------------ tiers and scores
@pytest.mark.parametrize("ctc,tier", [(4, 3), (6, 3), (9.99, 3), (10, 2), (12.5, 2), (14.99, 2), (15, 1), (40, 1)])
def test_tiers(ctc, tier):
    assert rules.tier_for_ctc(ctc) == tier


def test_override_moves_up_one_tier_only():
    assert rules.final_tier(3, True) == 2
    assert rules.final_tier(2, True) == 1
    assert rules.final_tier(1, True) == 1
    assert rules.final_tier(2, False) == 2


def test_package_curve():
    assert rules.package_score(0) == 0
    assert rules.package_score(6) == 3.0
    assert rules.package_score(10) == 5.5
    assert rules.package_score(15) == 8.0
    assert rules.package_score(25) == 10.0
    assert rules.package_score(60) == 10.0
    assert 5.5 < rules.package_score(12.5) < 8.0


def test_verdicts_and_cap():
    assert rules.verdict_for(7.0) == "Recommend"
    assert rules.verdict_for(6.9) == "Go with caution"
    assert rules.verdict_for(4.9) == "Avoid"
    flags = [{"flag": "Salary delays", "severity": "high", "source_count": 2}]
    assert rules.apply_red_flag_cap("Recommend", flags) == ("Go with caution", "Salary delays")
    one = [{"flag": "One angry post", "severity": "high", "source_count": 1}]
    assert rules.apply_red_flag_cap("Recommend", one) == ("Recommend", None)
    assert rules.apply_red_flag_cap("Avoid", flags) == ("Avoid", None)


def test_bond_flag():
    assert rules.bond_flag(0) is None
    assert rules.bond_flag(24)["severity"] == "high"
    assert rules.bond_flag(12)["severity"] == "medium"


def test_company_key():
    assert rules.company_key("Deloitte India Pvt. Ltd.") == rules.company_key("deloitte india")
    assert rules.company_key("  ICICI   Bank Limited ") == "icici bank"


def test_platform_detection():
    assert rules.platform_for("https://www.reddit.com/r/x") == "Reddit"
    assert rules.platform_for("https://www.ambitionbox.com/reviews/x") == "AmbitionBox"
    assert rules.platform_for("https://www.glassdoor.co.in/Reviews/x") == "Glassdoor"
    assert rules.platform_for("https://randomblog.in/x") == "Web"
    assert rules.platform_for("https://randomnews.in/x", "news") == "News"


# ------------------------------------------------------------------ consensus counting
SOURCES = [
    {"url": "https://reddit.com/a", "platform": "Reddit"},
    {"url": "https://reddit.com/b", "platform": "Reddit"},
    {"url": "https://ambitionbox.com/c", "platform": "AmbitionBox"},
    {"url": "https://reddit.com/a", "platform": "Reddit"},  # same URL twice
]


def test_consensus_levels():
    assert rules.consensus_label([0, 1, 2], SOURCES)["level"] == "wide"
    assert rules.consensus_label([0, 1], SOURCES)["level"] == "repeated"  # 2 sources, 1 platform
    assert rules.consensus_label([2], SOURCES)["level"] == "single"
    # duplicate URL counts once
    assert rules.consensus_label([0, 3], SOURCES)["sources"] == 1
    # three Reddit posts alone are "repeated", not "widely reported"
    reddit_only = [{"url": f"https://reddit.com/{i}", "platform": "Reddit"} for i in range(3)]
    assert rules.consensus_label([0, 1, 2], reddit_only)["level"] == "repeated"


def test_clean_ids_drops_bad_ids():
    assert rules.clean_ids([0, "1", 7, -1, "x", 1], 3) == [0, 1]


# ------------------------------------------------------------------ student reviews
def test_email_rules():
    assert valid_fiib_email("28-sarthak.mishra@fiib.edu.in")
    assert valid_fiib_email("A.B@FIIB.EDU.IN")
    assert not valid_fiib_email("someone@gmail.com")
    assert not valid_fiib_email("x@fiib.edu.in.evil.com")
    assert hash_email("A@fiib.edu.in", "s") == hash_email(" a@fiib.edu.in ", "s")


def _rev(**kw):
    base = {"pros": "Good training and helpful seniors in the team.", "cons": "Long hours at month end.",
            "interview": "", "rating_overall": 4, "rating_wlb": 3, "rating_culture": 4, "rating_growth": 4,
            "rating_management": 3, "created_at": "2020-01-01T00:00:00+00:00"}
    base.update(kw)
    return base


def test_heuristics():
    assert heuristic_flags(_rev(), []) == []
    assert "too_short" in heuristic_flags(_rev(pros="", cons="bad"), [])
    assert "extreme_ratings" in heuristic_flags(_rev(**{k: 5 for k in (
        "rating_overall", "rating_wlb", "rating_culture", "rating_growth", "rating_management")}), [])
    assert "near_duplicate" in heuristic_flags(_rev(), [_rev(cons="Long hours at month-end.")])
    now = datetime.now(timezone.utc).isoformat()
    burst = [_rev(pros=f"different text number {i} about the place", created_at=now) for i in range(4)]
    assert "burst" in heuristic_flags(_rev(), burst)


def test_credibility():
    assert credibility({"flags": [], "ai_match": "matches"})["level"] == "high"
    assert credibility({"flags": ["too_short"], "ai_match": "partly"})["level"] == "medium"
    assert credibility({"flags": ["too_short", "extreme_ratings"], "ai_match": "contradicts"})["level"] == "low"


# ------------------------------------------------------------------ building a record
FINDINGS = {
    "company_snapshot": "A firm.",
    "brand": {"score": 7, "reason": "Known."},
    "role": {"score": 12, "reason": "Core.", "role_type": "core"},  # out of range on purpose
    "environment": {"score": "6", "reason": "OK."},
    "external_ratings": [{"platform": "AmbitionBox", "rating": 4.05, "out_of": 5, "source_ids": [2]},
                         {"platform": "Made up", "rating": 5, "out_of": 5, "source_ids": [99]}],
    "claims": [
        {"topic": "Training", "statement": "Good training", "sentiment": "positive", "source_ids": [0, 1, 2]},
        {"topic": "Pay", "statement": "Invented claim", "sentiment": "negative", "source_ids": [42]},
        {"topic": "Culture", "statement": "One view", "sentiment": "mixed", "source_ids": [1],
         "fiib_review_ids": ["R-1", "R-unknown"]},
    ],
    "red_flags": [{"flag": "Salary delays", "severity": "high", "source_ids": [0, 2]},
                  {"flag": "No source flag", "severity": "high", "source_ids": []}],
    "fiib_review_checks": [{"review_id": "R-1", "match": "matches", "note": "ok"},
                           {"review_id": "R-zzz", "match": "matches", "note": "?"}],
    "exceptional": {"suggest": True, "reason": "Big name"},
    "evidence_quality": "strong",
    "summary": "Fine.",
}
SRC3 = [{"url": "https://reddit.com/a", "platform": "Reddit", "title": "a", "snippet": "a"},
        {"url": "https://reddit.com/b", "platform": "Reddit", "title": "b", "snippet": "b"},
        {"url": "https://ambitionbox.com/c", "platform": "AmbitionBox", "title": "c", "snippet": "c"}]


def test_build_record_guards_against_bad_ai_output():
    inp = {"company": "Acme Pvt Ltd", "role": "Analyst", "ctc_lpa": 16, "bond_months": 0}
    rec = pipeline.build_record(inp, SRC3, FINDINGS, [{"id": "R-1"}], "m", [])
    assert rec["tier"] == 1
    assert rec["scores"]["role"] == 10.0  # clamped
    assert rec["scores"]["environment"] == 6.0
    statements = [c["statement"] for c in rec["claims"]]
    assert "Invented claim" not in statements  # claim citing a non-existent source is dropped
    assert rec["claims"][0]["consensus"]["level"] == "wide"
    culture = next(c for c in rec["claims"] if c["topic"] == "Culture")
    assert culture["fiib_review_ids"] == ["R-1"]
    assert [f["flag"] for f in rec["red_flags"]] == ["Salary delays"]
    assert len(rec["external_ratings"]) == 1
    assert [c["review_id"] for c in rec["review_checks"]] == ["R-1"]
    # score would be Recommend, but the 2-source high red flag holds it at caution
    assert rules.total_score(rec["scores"]) >= 7
    assert rec["verdict"] == "Go with caution" and rec["verdict_capped_by"] == "Salary delays"


# ------------------------------------------------------------------ full run with fake web + AI
class FakeResp:
    def __init__(self, status, payload):
        self.status_code = status
        self._p = payload
        self.ok = 200 <= status < 300

    def json(self):
        return self._p

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(self.status_code)


def fake_post_factory(calls, gemini_status=None):
    gemini_status = list(gemini_status or [])

    def fake_post(url, json=None, headers=None, timeout=None, data=None):
        calls.append((url, json))
        if "tavily" in url:
            q = json["query"]
            return FakeResp(200, {"results": [
                {"title": f"{q} 1", "url": f"https://www.reddit.com/{abs(hash(q)) % 1000}/1", "content": "x"},
                {"title": f"{q} 2", "url": f"https://www.ambitionbox.com/{abs(hash(q)) % 1000}/2", "content": "y"},
            ]})
        status = gemini_status.pop(0) if gemini_status else 200
        if status != 200:
            return FakeResp(status, {})
        body = {"candidates": [{"content": {"parts": [{"text": "```json\n" + jsonlib.dumps(FINDINGS) + "\n```"}]}}]}
        return FakeResp(200, body)
    return fake_post


jsonlib = json


def test_full_run_with_fallback_model_and_cache(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(search.requests, "post", fake_post_factory(calls))
    monkeypatch.setattr(ai.requests, "post", fake_post_factory(calls, gemini_status=[404, 429]))
    store = storage.LocalStore(str(tmp_path / "s.json"))
    store.add("reviews", {"id": "R-1", "company_key": "acme", "company": "Acme", "hidden": False})
    inp = {"company": "Acme", "role": "Analyst", "ctc_lpa": 12, "bond_months": 0}

    rec = pipeline.run_assessment(inp, store, "g", "t")
    tav = [c for c in calls if "tavily" in c[0]]
    gem = [c for c in calls if "generativelanguage" in c[0]]
    assert len(tav) == 5
    assert len(gem) == 3  # 404 -> next model, 429 -> next model, then success
    assert rec["model"] == ai.C.GEMINI_MODELS[2]
    assert store.list("reviews")[0]["ai_match"] == "matches"

    calls.clear()
    pipeline.run_assessment(inp, store, "g", "t")  # second run reuses saved sources
    assert not [c for c in calls if "tavily" in c[0]]
    assert len(store.list("assessments")) == 2


def test_search_errors(monkeypatch):
    monkeypatch.setattr(search.requests, "post", lambda *a, **k: FakeResp(432, {}))
    with pytest.raises(search.SearchError, match="used up"):
        search.run_searches("t", "Acme", "Analyst")


def test_gemini_bad_key(monkeypatch):
    monkeypatch.setattr(ai.requests, "post", lambda *a, **k: FakeResp(403, {}))
    with pytest.raises(ai.AIError, match="rejected"):
        ai.analyse("g", "prompt")


# ------------------------------------------------------------------ storage
def test_sheet_store_round_trip(monkeypatch):
    sent = {}

    def fake_post(url, data=None, headers=None, timeout=None):
        sent["payload"] = jsonlib.loads(data)
        if sent["payload"]["action"] == "list":
            return FakeResp(200, {"ok": True, "data": [{"id": "A-1", "ctc_lpa": "12.5", "tier": 2.0,
                                                         "override": "FALSE", "claims": "[{\"a\": 1}]",
                                                         "scores": "{\"package\": 6}"}]})
        return FakeResp(200, {"ok": True})
    monkeypatch.setattr(storage.requests, "post", fake_post)
    st_ = storage.SheetStore("https://script.google.com/x", "tok")
    st_.add("assessments", {"id": "A-1", "claims": [{"a": 1}]})
    assert sent["payload"]["token"] == "tok"
    assert sent["payload"]["record"]["claims"] == '[{"a": 1}]'
    row = st_.list("assessments")[0]
    assert row["ctc_lpa"] == 12.5 and row["tier"] == 2 and row["override"] is False
    assert row["claims"] == [{"a": 1}] and row["scores"] == {"package": 6}


# ------------------------------------------------------------------ html safety
def test_html_is_escaped():
    evil = '<img src=x onerror=alert(1)>'
    rev = {"role": evil, "relation": "x", "year": "2026", "pros": evil, "cons": "", "interview": "",
           "rating_overall": 3, "flags": [], "created_at": "2026-01-01T00:00:00+00:00"}
    out = ui.review_card(rev)
    assert "<img" not in out
    src = [{"url": "javascript:alert(1)", "platform": "Web", "title": evil, "snippet": evil, "published": ""}]
    out = ui.sources_html({"sources": src})
    assert "javascript:" not in out and "<img" not in out


def test_news_outlets_count_separately():
    news = [{"url": f"https://www.{d}/x", "platform": "News"} for d in ("livemint.com", "reuters.com", "bbc.com")]
    assert rules.consensus_label([0, 1, 2], news)["level"] == "wide"
    assert ui.chip_label(news[0]) == "livemint.com"


def test_search_retries_once(monkeypatch):
    n = {"calls": 0}

    def flaky(*a, **k):
        n["calls"] += 1
        if n["calls"] % 2 == 1:
            raise search.requests.ConnectionError("blip")
        return FakeResp(200, {"results": [{"title": "t", "url": f"https://reddit.com/{n['calls']}", "content": "c"}]})
    monkeypatch.setattr(search.requests, "post", flaky)
    sources, warnings = search.run_searches("t", "Acme", "Analyst")
    assert len(sources) == 5 and warnings == []


def test_gemini_busy_is_retried_then_succeeds(monkeypatch):
    calls = []
    monkeypatch.setattr(ai.time, "sleep", lambda s: None)
    monkeypatch.setattr(ai.requests, "post", fake_post_factory(calls, gemini_status=[503, 503]))
    findings, model = ai.analyse("g", "prompt")
    assert model == ai.C.GEMINI_MODELS[0] and len(calls) == 3


def test_busy_gemini_keeps_sources_for_retry(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(ai.time, "sleep", lambda s: None)
    tavily_ok = fake_post_factory(calls)

    def busy_gemini(url, *a, **k):  # search works, Gemini is always busy
        return tavily_ok(url, *a, **k) if "tavily" in url else FakeResp(503, {})
    monkeypatch.setattr(search.requests, "post", busy_gemini)
    store = storage.LocalStore(str(tmp_path / "s.json"))
    inp = {"company": "Acme", "role": "Analyst", "ctc_lpa": 12, "bond_months": 0}
    with pytest.raises(ai.AIError, match="busy") as err:
        pipeline.run_assessment(inp, store, "g", "t")
    saved = err.value.sources
    assert len(saved) == 10
    calls.clear()
    monkeypatch.setattr(ai.requests, "post", fake_post_factory(calls))
    rec = pipeline.run_assessment(inp, store, "g", "t", cached_sources=saved)
    assert not [c for c in calls if "tavily" in c[0]] and rec["sources"] == saved
