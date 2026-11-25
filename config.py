"""All the rules the CMC may want to tweak live in this one file."""

# ---------------------------------------------------------------------------
# Tiers (based on total CTC in lakhs per annum)
#   Tier 1: 15 L and above
#   Tier 2: 10 L up to (not including) 15 L
#   Tier 3: below 10 L (offers below 6 L are Tier 3 too)
# ---------------------------------------------------------------------------
TIER_1_MIN = 15.0
TIER_2_MIN = 10.0

TIER_INFO = {
    1: {"name": "Tier 1", "range": "₹15 L and above"},
    2: {"name": "Tier 2", "range": "₹10 L to ₹15 L"},
    3: {"name": "Tier 3", "range": "Below ₹10 L"},
}

# ---------------------------------------------------------------------------
# Scoring weights (must add up to 1.0). Package matters most, as the Dean asked.
# ---------------------------------------------------------------------------
WEIGHTS = {
    "package": 0.40,
    "brand": 0.20,
    "role": 0.20,
    "environment": 0.20,
}

# Package score curve: (CTC in lakhs, score out of 10). Straight lines in between.
PACKAGE_CURVE = [(0, 0.0), (6, 3.0), (10, 5.5), (15, 8.0), (25, 10.0)]

# Verdict cut-offs on the final score out of 10
RECOMMEND_MIN = 7.0
CAUTION_MIN = 5.0

# A serious red flag reported by at least this many independent sources
# caps the verdict at "Go with caution".
RED_FLAG_CAP_SOURCES = 2

# A service bond this long (months) or longer is treated as a serious red flag.
BOND_SERIOUS_MONTHS = 24
BOND_NOTABLE_MONTHS = 12

# ---------------------------------------------------------------------------
# "How many people are saying this?"
# ---------------------------------------------------------------------------
WIDELY_REPORTED_MIN_SOURCES = 3   # and from at least 2 different platforms
REPEATED_MIN_SOURCES = 2

# Reuse saved search results for the same company for this many days
# (saves free search credits).
SEARCH_CACHE_DAYS = 14

# ---------------------------------------------------------------------------
# Student review guard
# ---------------------------------------------------------------------------
FIIB_EMAIL_DOMAIN = "fiib.edu.in"
MIN_REVIEW_CHARS = 40
NEAR_DUPLICATE_RATIO = 0.85
BURST_WINDOW_HOURS = 24
BURST_MIN_REVIEWS = 5

# ---------------------------------------------------------------------------
# Web searches run for each assessment (each one = 1 free Tavily credit)
# ---------------------------------------------------------------------------
REVIEW_SITES = ["ambitionbox.com", "glassdoor.co.in", "glassdoor.com", "indeed.com"]

SEARCH_PLAN = [
    {
        "key": "reviews",
        "label": "Employee reviews on AmbitionBox and Glassdoor",
        "query": "{company} employee reviews work culture rating",
        "include_domains": REVIEW_SITES,
        "topic": "general",
    },
    {
        "key": "reddit",
        "label": "Discussions on Reddit",
        "query": "{company} {role} work experience",
        "include_domains": ["reddit.com"],
        "topic": "general",
    },
    {
        "key": "role",
        "label": "Salary and interview reports for the role",
        "query": "{company} {role} salary interview experience",
        "include_domains": REVIEW_SITES + ["naukri.com", "linkedin.com"],
        "include_domains_mode": "prefer",
        "topic": "general",
    },
    {
        "key": "news",
        "label": "News from the last year",
        "query": "{company} layoffs hiring news",
        "topic": "news",
        "time_range": "year",
    },
    {
        "key": "profile",
        "label": "Company profile",
        "query": "{company} company profile India revenue employees",
        "topic": "general",
    },
]

# Gemini models tried in order (free tier). The first one that works is used.
GEMINI_MODELS = [
    "gemini-3.6-flash",
    "gemini-flash-latest",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
]

PLATFORMS = {
    "reddit.com": "Reddit",
    "ambitionbox.com": "AmbitionBox",
    "glassdoor.co.in": "Glassdoor",
    "glassdoor.com": "Glassdoor",
    "indeed.com": "Indeed",
    "naukri.com": "Naukri",
    "linkedin.com": "LinkedIn",
    "economictimes.indiatimes.com": "News",
    "livemint.com": "News",
    "moneycontrol.com": "News",
    "business-standard.com": "News",
    "thehindubusinessline.com": "News",
    "inc42.com": "News",
    "entrackr.com": "News",
}
