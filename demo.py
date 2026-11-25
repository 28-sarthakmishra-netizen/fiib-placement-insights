"""Sample data for demo mode (no API keys yet). Every company here is fictional."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pipeline import build_record
from rules import company_key


def _src(platform, title, snippet, found_by="reviews", published=""):
    slug = title.lower().replace(" ", "-")[:40]
    return {"title": title, "url": f"https://example.com/sample/{platform.lower()}/{slug}", "snippet": snippet,
            "platform": platform, "found_by": found_by, "published": published}


def _ago(days: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")


COMPANIES = [
    {
        "inp": {"company": "Northwind Analytics (Demo)", "role": "Financial Analyst", "ctc_lpa": 12.5,
                "location": "Gurugram", "bond_months": 0, "assessed_by": "CMC (sample)"},
        "days_ago": 2,
        "sources": [
            _src("AmbitionBox", "Northwind Analytics reviews",
                 "Rated 4.0 out of 5 from about 2,300 employee reviews. Employees praise structured "
                 "training and learning; several mention long hours around quarter-end."),
            _src("Glassdoor", "Working at Northwind Analytics",
                 "3.9 out of 5. Managers are approachable and the hybrid policy is flexible."),
            _src("Reddit", "Northwind FA role for freshers, worth it?",
                 "Training in the first three months is solid. Quarter-end crunch means 11 to 12 "
                 "hour days for a couple of weeks.", "reddit"),
            _src("Reddit", "Northwind vs other analytics firms for MBA freshers",
                 "Learning is great, appraisal hikes are average, around 8 to 10 percent.", "reddit"),
            _src("AmbitionBox", "Financial Analyst salaries at Northwind",
                 "Financial Analysts earn roughly ₹9.8 L to ₹14 L a year.", "role"),
            _src("News", "Northwind Analytics expands Gurugram centre, to hire 400",
                 "The firm is expanding its research centre and plans to hire 400 people this year.",
                 "news", "2026-09-14"),
            _src("Glassdoor", "Northwind Analytics interview questions",
                 "Aptitude test, a case study on financial statements, then an HR round.", "role"),
            _src("Web", "Northwind Analytics company profile",
                 "Mid-size analytics and financial research firm with around 6,000 employees.",
                 "profile"),
        ],
        "findings": {
            "company_snapshot": "A mid-size analytics and financial research firm with about 6,000 "
                                "employees. It is growing its Gurugram centre.",
            "brand": {"score": 6.5, "reason": "Known in analytics and research circles, not a household name."},
            "role": {"score": 8, "reason": "Core finance work with real statements and models; fits PGDM FM.",
                     "role_type": "core"},
            "environment": {"score": 7, "reason": "Good ratings and training; crunch weeks at quarter-end."},
            "external_ratings": [
                {"platform": "AmbitionBox", "rating": 4.0, "out_of": 5, "based_on": "about 2,300 reviews",
                 "source_ids": [0]},
                {"platform": "Glassdoor", "rating": 3.9, "out_of": 5, "based_on": "", "source_ids": [1]},
            ],
            "claims": [
                {"topic": "Training", "statement": "Training for freshers is structured and genuinely useful.",
                 "sentiment": "positive", "source_ids": [0, 2, 3], "fiib_review_ids": ["R-demo01"]},
                {"topic": "Work-life balance", "statement": "Long hours for a few weeks around every quarter-end.",
                 "sentiment": "negative", "source_ids": [0, 2], "fiib_review_ids": ["R-demo01"]},
                {"topic": "Job security", "statement": "The company is expanding and hiring, not cutting.",
                 "sentiment": "positive", "source_ids": [5, 7]},
                {"topic": "Pay", "statement": "Yearly hikes are average, around 8 to 10 percent.",
                 "sentiment": "mixed", "source_ids": [3]},
                {"topic": "Managers", "statement": "Managers are approachable and the hybrid policy is flexible.",
                 "sentiment": "positive", "source_ids": [1]},
            ],
            "red_flags": [],
            "fiib_review_checks": [
                {"review_id": "R-demo01", "match": "matches",
                 "note": "Training and quarter-end hours are also reported on AmbitionBox and Reddit."},
                {"review_id": "R-demo02", "match": "contradicts",
                 "note": "Says there is no training at all; three outside sources say the opposite."},
            ],
            "exceptional": {"suggest": False, "reason": ""},
            "evidence_quality": "strong",
            "summary": "A good first job for finance students who want hands-on analysis. Expect strong "
                       "training and decent managers, with a few heavy weeks every quarter. Pay growth is "
                       "average, so the learning is the main reason to join.",
        },
    },
    {
        "inp": {"company": "Bluepeak Capital (Demo)", "role": "Investment Banking Analyst", "ctc_lpa": 18,
                "location": "Mumbai", "bond_months": 0, "assessed_by": "CMC (sample)"},
        "days_ago": 5,
        "sources": [
            _src("Glassdoor", "Bluepeak Capital reviews",
                 "4.1 out of 5. Steep learning curve, excellent exposure to live deals, very long hours."),
            _src("AmbitionBox", "Bluepeak Capital employee reviews",
                 "Rated 3.8 from about 900 reviews. Work-life balance rated lowest at 2.6."),
            _src("Reddit", "IB analyst life at Bluepeak",
                 "80-hour weeks during live deals are normal. You learn more in a year than most places "
                 "in three.", "reddit"),
            _src("Reddit", "Bluepeak bonus season", "Bonuses were strong this year, on top of a high fixed pay.",
                 "reddit"),
            _src("Reddit", "One MD at Bluepeak made my life hell",
                 "One managing director in my group was abusive; other groups seemed fine.", "reddit"),
            _src("AmbitionBox", "Investment Banking Analyst salary at Bluepeak",
                 "Analysts earn ₹16 L to ₹22 L a year including bonus.", "role"),
            _src("News", "Bluepeak advises on three of the year's largest IPOs",
                 "The bank was an adviser on three large IPOs this year.", "news", "2026-08-02"),
        ],
        "findings": {
            "company_snapshot": "A well-known investment bank in India's capital markets. It advised on several "
                                "large IPOs this year.",
            "brand": {"score": 8, "reason": "A recognised name in Indian investment banking."},
            "role": {"score": 9, "reason": "Front-office deal work; the best finance launchpad a fresher can get.",
                     "role_type": "core"},
            "environment": {"score": 5, "reason": "Great learning, but very long hours are standard."},
            "external_ratings": [
                {"platform": "Glassdoor", "rating": 4.1, "out_of": 5, "based_on": "", "source_ids": [0]},
                {"platform": "AmbitionBox", "rating": 3.8, "out_of": 5, "based_on": "about 900 reviews",
                 "source_ids": [1]},
            ],
            "claims": [
                {"topic": "Work-life balance", "statement": "Very long hours, often 80 a week during live deals.",
                 "sentiment": "negative", "source_ids": [0, 1, 2]},
                {"topic": "Growth", "statement": "Learning and deal exposure are exceptional.",
                 "sentiment": "positive", "source_ids": [0, 2, 6]},
                {"topic": "Pay", "statement": "High fixed pay with strong bonuses.", "sentiment": "positive",
                 "source_ids": [3, 5]},
                {"topic": "Managers", "statement": "One person reports an abusive managing director in one group.",
                 "sentiment": "negative", "source_ids": [4]},
            ],
            "red_flags": [{"flag": "One report of an abusive senior manager", "severity": "low",
                           "source_ids": [4]}],
            "fiib_review_checks": [],
            "exceptional": {"suggest": True, "reason": "Front-office IB role at a recognised bank."},
            "evidence_quality": "strong",
            "summary": "One of the strongest starts in finance: real deals, high pay and fast learning. "
                       "The price is very long hours. Only one person reports a bad manager, so treat that "
                       "as a single experience rather than the norm.",
        },
    },
    {
        "inp": {"company": "Crestline Retail Finance (Demo)", "role": "Relationship Manager", "ctc_lpa": 7.2,
                "location": "Delhi NCR", "bond_months": 18, "assessed_by": "CMC (sample)"},
        "days_ago": 9,
        "sources": [
            _src("AmbitionBox", "Crestline Retail Finance reviews",
                 "Rated 3.1 from about 4,000 reviews. Job security and work-life balance rated lowest. "
                 "Many reviews mention daily loan sales targets."),
            _src("Glassdoor", "Crestline employee reviews",
                 "2.9 out of 5. 'Relationship Manager' is a field sales role with daily targets."),
            _src("Reddit", "Crestline RM job reality", "It's loan sales. Targets every day, pressure from "
                 "the area manager, incentives are hard to get.", "reddit"),
            _src("Reddit", "Crestline salary delayed again",
                 "Salary credited 12 days late this month, second time this year.", "reddit"),
            _src("AmbitionBox", "Crestline salary credit delays",
                 "Several reviews this year mention delayed salary credit.", "reviews"),
            _src("Reddit", "Quick promotions at Crestline?", "Top performers get promoted within a year.",
                 "reddit"),
        ],
        "findings": {
            "company_snapshot": "A retail lending company that sells personal and business loans through "
                                "branches and field teams.",
            "brand": {"score": 4, "reason": "Known regionally; weak employer reputation."},
            "role": {"score": 3, "reason": "The title says relationship manager, but the work is loan sales "
                                           "against daily targets.", "role_type": "sales-heavy"},
            "environment": {"score": 3.5, "reason": "Low ratings, target pressure and salary delays."},
            "external_ratings": [
                {"platform": "AmbitionBox", "rating": 3.1, "out_of": 5, "based_on": "about 4,000 reviews",
                 "source_ids": [0]},
                {"platform": "Glassdoor", "rating": 2.9, "out_of": 5, "based_on": "", "source_ids": [1]},
            ],
            "claims": [
                {"topic": "Role reality", "statement": "The role is field loan sales with daily targets.",
                 "sentiment": "negative", "source_ids": [0, 1, 2], "fiib_review_ids": ["R-demo03"]},
                {"topic": "Pay", "statement": "Salaries have been credited late more than once this year.",
                 "sentiment": "negative", "source_ids": [3, 4]},
                {"topic": "Growth", "statement": "Top performers can be promoted within a year.",
                 "sentiment": "positive", "source_ids": [5]},
            ],
            "red_flags": [{"flag": "Delayed salary payments reported this year", "severity": "high",
                           "source_ids": [3, 4]}],
            "fiib_review_checks": [
                {"review_id": "R-demo03", "match": "matches",
                 "note": "Daily sales targets are reported on AmbitionBox, Glassdoor and Reddit."},
            ],
            "exceptional": {"suggest": False, "reason": ""},
            "evidence_quality": "strong",
            "summary": "Despite the title, this is a loan sales job with daily targets. Salary delays and an "
                       "18-month bond make it risky for a fresher. Only consider it if you want a sales career.",
        },
    },
    {
        "inp": {"company": "Orbit Fintech (Demo)", "role": "Business Analyst", "ctc_lpa": 10.8,
                "location": "Bengaluru", "bond_months": 0, "assessed_by": "CMC (sample)"},
        "days_ago": 14,
        "sources": [
            _src("News", "Orbit Fintech lays off 8% of staff", "The payments startup cut about 8% of its "
                 "workforce in a restructuring.", "news", "2026-03-20"),
            _src("Reddit", "Orbit layoffs, which teams?", "Mostly sales and support. Analytics team was "
                 "untouched but morale is low.", "reddit"),
            _src("Glassdoor", "Orbit Fintech reviews", "3.6 out of 5. Real product exposure, fast pace, "
                 "priorities change often."),
            _src("AmbitionBox", "Orbit Fintech reviews", "Rated 3.5. Good learning; processes are chaotic."),
            _src("AmbitionBox", "Business Analyst salary at Orbit", "Business Analysts earn ₹9 L to ₹13 L.", "role"),
        ],
        "findings": {
            "company_snapshot": "A payments startup that went through a restructuring this year.",
            "brand": {"score": 5.5, "reason": "Known in fintech; startup-level brand."},
            "role": {"score": 7, "reason": "Analytics on a live product, useful experience.", "role_type": "core"},
            "environment": {"score": 5.5, "reason": "Fast learning, but layoffs and changing priorities."},
            "external_ratings": [
                {"platform": "Glassdoor", "rating": 3.6, "out_of": 5, "based_on": "", "source_ids": [2]},
                {"platform": "AmbitionBox", "rating": 3.5, "out_of": 5, "based_on": "", "source_ids": [3]},
            ],
            "claims": [
                {"topic": "Growth", "statement": "Hands-on exposure to a live product and fast learning.",
                 "sentiment": "positive", "source_ids": [2, 3]},
                {"topic": "Job security", "statement": "About 8% of staff were laid off this year.",
                 "sentiment": "negative", "source_ids": [0, 1]},
                {"topic": "Culture", "statement": "Priorities change often and processes are chaotic.",
                 "sentiment": "mixed", "source_ids": [2, 3]},
            ],
            "red_flags": [{"flag": "Layoffs this year (about 8% of staff)", "severity": "medium",
                           "source_ids": [0, 1]}],
            "fiib_review_checks": [],
            "exceptional": {"suggest": False, "reason": ""},
            "evidence_quality": "moderate",
            "summary": "Good hands-on analytics experience at a fast-moving startup. The layoffs earlier this "
                       "year mostly hit sales and support, but job security is weaker than at a large firm.",
        },
    },
]

REVIEWS = [
    {"id": "R-demo01", "company": "Northwind Analytics (Demo)", "role": "Financial Analyst Intern",
     "relation": "Interned there", "year": "2026", "rating_overall": 4, "rating_wlb": 3,
     "rating_culture": 4, "rating_growth": 5, "rating_management": 4,
     "pros": "Proper training in the first month, my manager reviewed every model with me.",
     "cons": "The last two weeks of the quarter were 12-hour days.",
     "interview": "Aptitude test, then a case on a balance sheet, then HR.", "flags": [],
     "ai_match": "matches", "ai_note": "Training and quarter-end hours are also reported on AmbitionBox and Reddit.",
     "days_ago": 20},
    {"id": "R-demo02", "company": "Northwind Analytics (Demo)", "role": "Analyst", "relation": "Interviewed only",
     "year": "2026", "rating_overall": 1, "rating_wlb": 1, "rating_culture": 1, "rating_growth": 1,
     "rating_management": 1, "pros": "", "cons": "Worst company, no training.", "interview": "",
     "flags": ["too_short", "extreme_ratings"], "ai_match": "contradicts",
     "ai_note": "Says there is no training at all; three outside sources say the opposite.", "days_ago": 3},
    {"id": "R-demo03", "company": "Crestline Retail Finance (Demo)", "role": "Relationship Manager",
     "relation": "Worked there before", "year": "2025", "rating_overall": 2, "rating_wlb": 2,
     "rating_culture": 2, "rating_growth": 3, "rating_management": 2,
     "pros": "You learn to talk to customers and handle rejection.",
     "cons": "It is pure loan sales. Daily targets and calls from the area manager every evening.",
     "interview": "One HR call and one round with the branch head about sales targets.", "flags": [],
     "ai_match": "matches", "ai_note": "Daily sales targets are reported on AmbitionBox, Glassdoor and Reddit.",
     "days_ago": 40},
]


def seed(store) -> None:
    for c in COMPANIES:
        rev = [r for r in REVIEWS if r["company"] == c["inp"]["company"]]
        rec = build_record(c["inp"], c["sources"], c["findings"], rev, "sample data", [])
        rec["created_at"] = _ago(c["days_ago"])
        rec["demo"] = True
        store.add("assessments", rec)
    for r in REVIEWS:
        r = dict(r)
        days = r.pop("days_ago")
        r.update({"company_key": company_key(r["company"]), "created_at": _ago(days),
                  "email_hash": "sample", "hidden": False, "demo": True})
        store.add("reviews", r)


def sample_run() -> dict:
    c = COMPANIES[0]
    rev = [r for r in REVIEWS if r["company"] == c["inp"]["company"]]
    rec = build_record(c["inp"], c["sources"], c["findings"], rev, "sample data", [])
    rec["demo"] = True
    return rec
