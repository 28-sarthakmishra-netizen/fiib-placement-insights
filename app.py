"""FIIB Placement Insights: tier, reality check and verdict for every campus offer."""
from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from core import config as C, demo, rules
from core.ai import AIError
from core.pipeline import run_assessment
from core.reviews import (AI_MATCH, FLAG_TEXT, RATING_FIELDS, credibility, hash_email,
                          heuristic_flags, now_iso, valid_fiib_email)
from core.search import SearchError
from core.storage import LocalStore, SheetError, SheetStore, new_id
from ui import components as ui

HERE = os.path.dirname(os.path.abspath(__file__))
st.set_page_config(page_title="FIIB Placement Insights", page_icon=os.path.join(HERE, "static", "icon.png"),
                   layout="wide")


# ------------------------------------------------------------------ settings and storage
def secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default) or default).strip()
    except Exception:  # no secrets file at all
        return os.environ.get(name, default).strip()


GEMINI_KEY = secret("GEMINI_API_KEY")
TAVILY_KEY = secret("TAVILY_API_KEY")
SHEET_URL = secret("SHEETS_WEBAPP_URL")
SHEET_TOKEN = secret("SHEETS_TOKEN")
CMC_PASSCODE = secret("CMC_PASSCODE")
REVIEW_SALT = secret("REVIEW_SALT", "fiib-placement-insights")
GEMINI_MODEL = secret("GEMINI_MODEL")
DEMO = not (GEMINI_KEY and TAVILY_KEY)


@st.cache_resource
def get_store():
    if SHEET_URL and SHEET_TOKEN:
        return SheetStore(SHEET_URL, SHEET_TOKEN)
    if DEMO:
        path = os.path.join(HERE, "data", "demo_store.json")
        fresh = not os.path.exists(path)
        store = LocalStore(path)
        if fresh:
            demo.seed(store)
        return store
    return LocalStore(os.path.join(HERE, "data", "store.json"))


STORE = get_store()


@st.cache_data(ttl=60, show_spinner=False)
def load(table: str) -> list[dict]:
    return STORE.list(table)


def refresh():
    load.clear()


def assessments() -> list[dict]:
    try:
        return load("assessments")
    except SheetError as e:
        st.error(str(e))
        return []


def reviews() -> list[dict]:
    try:
        return load("reviews")
    except SheetError as e:
        st.error(str(e))
        return []


def latest_by_company() -> list[dict]:
    latest: dict[str, dict] = {}
    for a in assessments():
        k = a["company_key"]
        if k not in latest or a["created_at"] > latest[k]["created_at"]:
            latest[k] = a
    return sorted(latest.values(), key=lambda a: a["created_at"], reverse=True)


def cmc_gate() -> bool:
    if not CMC_PASSCODE:
        if not DEMO:
            st.warning("No CMC passcode is set, so anyone with the link can use this page. "
                       "Add CMC_PASSCODE in the app's secrets before sharing the link.")
        return True
    if st.session_state.get("cmc_ok"):
        return True
    with st.form("gate"):
        code = st.text_input("CMC passcode", type="password")
        if st.form_submit_button("Unlock", type="primary"):
            if code == CMC_PASSCODE:
                st.session_state.cmc_ok = True
                st.rerun()
            st.error("That passcode is wrong.")
    return False


def demo_banner():
    if DEMO:
        st.html('<div class="pi-banner">You are looking at sample data. The companies marked Sample are '
                'made up to show how the app works. Add the free Gemini and Tavily keys to assess real '
                'companies (see the setup guide).</div>')


# ------------------------------------------------------------------ company detail
def render_assessment(a: dict, company_reviews: list[dict], show_back: bool = True):
    if show_back and st.button("Back to all companies", icon=":material/arrow_back:", type="tertiary"):
        st.query_params.clear()
        st.rerun()

    loc = f", {ui.esc(a['location'])}" if a.get("location") else ""
    demo_tag = ' <span class="pi-demo">Sample</span>' if a.get("demo") else ""
    by = f" by {ui.esc(a['assessed_by'])}" if a.get("assessed_by") else ""
    st.html(f'<div class="pi-hero"><h1>{ui.esc(a["company"])}{demo_tag}</h1>'
            f'<p>{ui.esc(a["role"])}{loc}. Assessed {ui.fmt_date(a["created_at"])}{by}.</p>'
            f'<div style="margin-top:.7rem">{ui.tier_chip(a["tier"], a.get("override"))}</div></div>')
    st.html(ui.ruler(a["ctc_lpa"]))
    if a.get("override") and a.get("override_reason"):
        st.caption(f"Moved up from Tier {a['base_tier']} by CMC: {a['override_reason']}")
    st.html(ui.verdict_panel(a))

    st.write("")
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        st.subheader("How the score adds up")
        st.html(ui.score_bars(a))
    with right:
        st.subheader("The company")
        st.write(a.get("snapshot") or "No profile found.")
        st.html(ui.ratings_html(a))
        quality = {"strong": "Plenty of sources agree.", "moderate": "A fair number of sources.",
                   "thin": "Very few sources. Check this one by hand before advising students."}
        st.caption(f"Evidence: {quality.get(a.get('evidence_quality'), '')}")
        if a.get("ai_suggests_exceptional") and not a.get("override") and a["base_tier"] > 1:
            st.info(f"The AI thinks this could count as an exceptional brand or role: "
                    f"{a.get('ai_exceptional_reason', '')} The CMC can move it up a tier when assessing.",
                    icon=":material/workspace_premium:")
        for w in a.get("warnings") or []:
            st.caption(w)

    visible = [r for r in company_reviews if not r.get("hidden")]
    t1, t2, t3, t4 = st.tabs([
        f"What people say ({len(a['claims'])})",
        f"Red flags ({len(a.get('red_flags') or [])})",
        f"FIIB reviews ({len(visible)})",
        f"Sources ({len(a['sources'])})",
    ])
    with t1:
        st.html(ui.claims_html(a))
    with t2:
        st.html(ui.flags_html(a))
    with t3:
        if not visible:
            st.write("No FIIB student has reviewed this company yet.")
        else:
            visible.sort(key=lambda r: credibility(r)["score"], reverse=True)
            st.html("".join(ui.review_card(r) for r in visible))
            st.caption("Scores come from outside sources only. Student reviews are checked against them, and low-credibility ones are faded.")
        if st.button("Share your experience with this company", icon=":material/rate_review:"):
            st.session_state.review_company = a["company"]
            st.switch_page(PAGES["review"])
    with t4:
        st.html(ui.sources_html(a))


# ------------------------------------------------------------------ pages
def page_companies():
    key = st.query_params.get("company")
    data = latest_by_company()
    if key:
        match = [a for a in data if a["company_key"] == key]
        if match:
            render_assessment(match[0], [r for r in reviews() if r.get("company_key") == key])
            return
        st.query_params.clear()

    st.html('<div class="pi-hero"><h1>Which company is coming to campus?</h1>'
            '<p>Each offer gets a tier from its CTC, a check against what employees say on AmbitionBox, '
            'Glassdoor, Reddit and the news, and a clear verdict for students.</p></div>')
    demo_banner()

    if not data:
        st.write("No companies have been assessed yet.")
        if st.button("Assess the first offer", type="primary"):
            st.switch_page(PAGES["assess"])
        return

    tiers = [a["tier"] for a in data]
    ctcs = sorted(a["ctc_lpa"] for a in data)
    median = ctcs[len(ctcs) // 2] if len(ctcs) % 2 else (ctcs[len(ctcs) // 2 - 1] + ctcs[len(ctcs) // 2]) / 2
    rec = sum(1 for a in data if a["verdict"] == "Recommend")
    st.html('<div class="pi-stats">'
            f'<div class="pi-stat"><b>{len(data)}</b><span>companies assessed</span></div>'
            f'<div class="pi-stat"><b style="color:var(--tier1)">{tiers.count(1)}</b><span>Tier 1 offers</span></div>'
            f'<div class="pi-stat"><b style="color:var(--tier2)">{tiers.count(2)}</b><span>Tier 2 offers</span></div>'
            f'<div class="pi-stat"><b style="color:var(--tier3)">{tiers.count(3)}</b><span>Tier 3 offers</span></div>'
            f'<div class="pi-stat"><b>{ui.fmt_lpa(round(median, 1))}</b><span>median CTC</span></div>'
            f'<div class="pi-stat"><b style="color:var(--go)">{rec}</b><span>recommended</span></div></div>')

    c1, c2, c3, c4 = st.columns([1.25, 1.05, 2.0, 0.85], vertical_alignment="bottom")
    q = c1.text_input("Search", placeholder="Company or role", label_visibility="collapsed")
    tier_f = c2.pills("Tier", [1, 2, 3], format_func=lambda t: f"Tier {t}", selection_mode="multi",
                      label_visibility="collapsed")
    verdict_f = c3.pills("Verdict", ["Recommend", "Go with caution", "Avoid"], selection_mode="multi",
                         label_visibility="collapsed")
    sort = c4.selectbox("Sort", ["Newest", "Highest score", "Highest CTC"], label_visibility="collapsed")

    rows = data
    if q:
        ql = q.lower()
        rows = [a for a in rows if ql in a["company"].lower() or ql in a["role"].lower()]
    if tier_f:
        rows = [a for a in rows if a["tier"] in tier_f]
    if verdict_f:
        rows = [a for a in rows if a["verdict"] in verdict_f]
    if sort == "Highest score":
        rows = sorted(rows, key=lambda a: a["score"], reverse=True)
    elif sort == "Highest CTC":
        rows = sorted(rows, key=lambda a: a["ctc_lpa"], reverse=True)

    st.write("")
    if not rows:
        st.write("No company matches these filters.")
    for a in rows:
        c_row, c_btn = st.columns([12, 1.6], vertical_alignment="center")
        c_row.html(ui.company_row(a))
        if c_btn.button("Open", key=f"open_{a['id']}", width="stretch"):
            st.query_params["company"] = a["company_key"]
            st.rerun()


def page_assess():
    st.html('<div class="pi-hero"><h1>Assess a new offer</h1><p>Enter what the company is offering. '
            'The tier updates as you type; the full check takes about a minute.</p></div>')
    if not cmc_gate():
        return
    demo_banner()

    c1, c2 = st.columns(2)
    company = c1.text_input("Company", placeholder="As written on the job description")
    role = c2.text_input("Role", placeholder="For example, Financial Analyst")
    c3, c4, c5 = st.columns(3)
    ctc = c3.number_input("Total CTC (₹ lakh a year)", min_value=0.0, max_value=200.0, value=0.0, step=0.5,
                          format="%.1f")
    location = c4.text_input("Location", placeholder="City")
    bond = c5.number_input("Service bond (months)", min_value=0, max_value=60, value=0, step=6,
                           help="Enter 0 if there is no bond.")

    base = rules.tier_for_ctc(ctc) if ctc > 0 else None
    st.html(ui.ruler(ctc if ctc > 0 else None))

    override, reason = False, ""
    if base and base > 1:
        override = st.checkbox(f"Exceptional brand or role: move this offer up to Tier {base - 1}")
        if override:
            reason = st.text_input("Why is it exceptional?", placeholder="For example, top global consulting firm")
    if base:
        tier = rules.final_tier(base, override)
        st.html(f'<p>This offer will be {ui.tier_chip(tier, override)} '
                f'<span class="pi-muted">({C.TIER_INFO[base]["range"]})</span></p>')

    c6, c7 = st.columns(2)
    assessed_by = c6.text_input("Your name", placeholder="Shown on the assessment")
    fresh = c7.checkbox("Search the web again even if this company was checked recently",
                        help=f"Results are reused for {C.SEARCH_CACHE_DAYS} days to save free searches.")

    label = "Run sample assessment" if DEMO else "Run assessment"
    if not st.button(label, type="primary", icon=":material/travel_explore:"):
        return

    if DEMO:
        import time
        with st.status("Running the sample assessment", expanded=True) as status:
            for step in C.SEARCH_PLAN:
                st.write(f"Searching: {step['label']}")
                time.sleep(0.35)
            st.write("Reading 8 sources and 2 FIIB reviews")
            time.sleep(0.6)
            st.write("Counting sources and scoring")
            time.sleep(0.3)
            status.update(label="Sample assessment ready", state="complete", expanded=False)
        st.info("This is the sample company, not the one you typed. Add the free API keys to assess real "
                "companies.", icon=":material/info:")
        a = demo.sample_run()
        render_assessment(a, [r for r in reviews() if r.get("company_key") == a["company_key"]],
                          show_back=False)
        return

    errors = []
    if not company.strip():
        errors.append("Enter the company name.")
    if not role.strip():
        errors.append("Enter the role.")
    if ctc <= 0:
        errors.append("Enter the total CTC.")
    if override and not reason.strip():
        errors.append("Say why the brand or role is exceptional.")
    if errors:
        for e in errors:
            st.error(e)
        return

    inp = {"company": company, "role": role, "ctc_lpa": ctc, "location": location, "bond_months": bond,
           "override": override, "override_reason": reason, "assessed_by": assessed_by, "fresh_search": fresh}
    a, problem = None, None
    with st.status(f"Assessing {company}", expanded=True) as status:
        def on_step(kind, text):
            st.write(("Searching: " if kind == "search" else "") + text)
        try:
            a = run_assessment(inp, STORE, GEMINI_KEY, TAVILY_KEY, GEMINI_MODEL or None, on_step)
            status.update(label=f"{company} assessed", state="complete", expanded=False)
        except (SearchError, AIError, SheetError) as e:
            problem = str(e)
        except Exception as e:  # anything unexpected: show it plainly instead of a traceback
            problem = (f"Something unexpected went wrong ({type(e).__name__}: {e}). Try again; if it keeps "
                       "happening, send this message to whoever set up the app.")
        if problem:
            status.update(label="The assessment stopped", state="error", expanded=False)
    if problem:
        st.error(problem)
        return
    refresh()
    st.toast(f"{company} saved to the company list", icon=":material/check_circle:")
    render_assessment(a, [r for r in reviews() if r.get("company_key") == a["company_key"]], show_back=False)


def page_review():
    st.html('<div class="pi-hero"><h1>Share what it was really like</h1><p>Interned, worked or interviewed '
            'somewhere? Your review helps the next batch. Your name and email are never shown.</p></div>')

    names = sorted({a["company"] for a in latest_by_company()})
    other = "Another company"
    pre = st.session_state.pop("review_company", None)
    idx = names.index(pre) if pre in names else None
    pick = st.selectbox("Company", names + [other], index=idx, placeholder="Choose a company")
    company = st.text_input("Company name") if pick == other else (pick or "")

    c1, c2 = st.columns(2)
    email = c1.text_input("Your FIIB email", placeholder=f"name@{C.FIIB_EMAIL_DOMAIN}",
                          help="Used only to allow one review per person per company. It is stored "
                               "scrambled and never shown.")
    role = c2.text_input("Your role there", placeholder="For example, Summer Intern, Finance")
    c3, c4 = st.columns([2, 1])
    relation = c3.pills("How do you know this company?", ["Interned there", "Working there now",
                                                          "Worked there before", "Interviewed only"])
    year = c4.selectbox("Year", [str(y) for y in range(2027, 2019, -1)], index=1)

    st.markdown("**Your ratings**")
    ratings = {}
    cols = st.columns(len(RATING_FIELDS))
    for col, (k, label) in zip(cols, RATING_FIELDS.items()):
        with col:
            st.caption(label)
            v = st.feedback("stars", key=f"rate_{k}")
            ratings[k] = (v + 1) if v is not None else 0

    pros = st.text_area("What did you like?", height=90)
    cons = st.text_area("What did you not like?", height=90)
    interview = st.text_area("How did the interview go? (rounds, questions, difficulty)", height=90)
    honest = st.checkbox("This is my own experience, and it is honest.")

    if not st.button("Post my review", type="primary", icon=":material/send:"):
        return
    errs = []
    if not company.strip():
        errs.append("Choose or type the company.")
    if not valid_fiib_email(email):
        errs.append(f"Use your FIIB email (ending in @{C.FIIB_EMAIL_DOMAIN}).")
    if not relation:
        errs.append("Say how you know the company.")
    if not ratings["rating_overall"]:
        errs.append("Give an overall rating.")
    if not honest:
        errs.append("Tick the box to confirm this is your own honest experience.")
    if errs:
        for e in errs:
            st.error(e)
        return

    key = rules.company_key(company)
    h = hash_email(email, REVIEW_SALT)
    same = [r for r in reviews() if r.get("company_key") == key]
    if any(r.get("email_hash") == h for r in same):
        st.error("You have already reviewed this company. Each person can post one review per company.")
        return
    rec = {"id": new_id("R"), "created_at": now_iso(), "company": company.strip(), "company_key": key,
           "role": role.strip(), "relation": relation, "year": year, "email_hash": h, **ratings,
           "pros": pros.strip(), "cons": cons.strip(), "interview": interview.strip(), "hidden": False,
           "ai_match": "", "ai_note": "", "demo": False}
    rec["flags"] = heuristic_flags(rec, same)
    try:
        STORE.add("reviews", rec)
    except SheetError as e:
        st.error(str(e))
        return
    refresh()
    st.success("Review posted. It will be checked against outside sources the next time this company is "
               "assessed.", icon=":material/check_circle:")


def page_panel():
    st.html('<div class="pi-hero"><h1>CMC panel</h1><p>Hide reviews that look fake, and download '
            'everything as spreadsheets.</p></div>')
    if not cmc_gate():
        return
    revs = reviews()
    data = assessments()

    flagged = [r for r in revs if credibility(r)["level"] == "low" and not r.get("hidden")]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Assessments", len(data))
    m2.metric("Student reviews", len(revs))
    m3.metric("Low credibility, still visible", len(flagged))
    m4.metric("Hidden reviews", sum(1 for r in revs if r.get("hidden")))

    st.subheader("Student reviews")
    if not revs:
        st.write("No reviews yet.")
    else:
        table = pd.DataFrame([{
            "id": r["id"], "Company": r["company"], "Role": r.get("role", ""), "Relation": r.get("relation", ""),
            "Overall": r.get("rating_overall", 0), "Credibility": credibility(r)["score"],
            "Flags": ", ".join(FLAG_TEXT.get(f, f) for f in (r.get("flags") or [])),
            "Outside check": AI_MATCH.get(r.get("ai_match"), ("",))[0],
            "Hidden": r.get("hidden", False), "Posted": ui.fmt_date(r.get("created_at", "")),
        } for r in sorted(revs, key=lambda r: credibility(r)["score"])])
        st.dataframe(table, hide_index=True, width="stretch",
                     column_config={"Credibility": st.column_config.ProgressColumn(
                         "Credibility", min_value=0, max_value=100, format="%d")})
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        rid = c1.selectbox("Review", table["id"].tolist(),
                           format_func=lambda i: f"{i}  {table.set_index('id').loc[i, 'Company']}")
        cur = next(r for r in revs if r["id"] == rid)
        if c2.button("Show review" if cur.get("hidden") else "Hide review", width="stretch"):
            STORE.update("reviews", rid, {"hidden": not cur.get("hidden")})
            refresh()
            st.rerun()
        st.html(ui.review_card(cur))

    st.subheader("Download")
    d1, d2 = st.columns(2)
    if data:
        flat = pd.DataFrame([{
            "Company": a["company"], "Role": a["role"], "CTC (L)": a["ctc_lpa"], "Tier": a["tier"],
            "Moved up": a.get("override"), "Score": a["score"], "Verdict": a["verdict"],
            "Package": a["scores"].get("package"), "Brand": a["scores"].get("brand"),
            "Role score": a["scores"].get("role"), "Environment": a["scores"].get("environment"),
            "Red flags": "; ".join(f["flag"] for f in a.get("red_flags") or []),
            "Sources": len(a["sources"]), "Assessed": ui.fmt_date(a["created_at"]),
            "By": a.get("assessed_by", ""),
        } for a in data])
        d1.download_button("Assessments (CSV)", flat.to_csv(index=False), "assessments.csv",
                           icon=":material/download:")
    if revs:
        d2.download_button("Reviews (CSV)", pd.DataFrame(revs).drop(columns=["email_hash"], errors="ignore")
                           .to_csv(index=False), "reviews.csv", icon=":material/download:")
    st.caption(f"Storage: {'Google Sheet' if STORE.kind == 'sheet' else 'local file on the server'}. "
               f"Mode: {'sample data' if DEMO else 'live'}.")


def page_method():
    st.html('<div class="pi-hero"><h1>How an offer is judged</h1><p>The tier and the final score follow '
            'fixed rules. The AI only reads the sources; the code does the counting.</p></div>')
    st.html(ui.ruler(None))
    w = C.WEIGHTS
    steps = [
        ("Tier from the CTC", f"Below ₹{C.TIER_2_MIN:g} L is Tier 3, ₹{C.TIER_2_MIN:g} L to ₹{C.TIER_1_MIN:g} L is "
                              f"Tier 2, ₹{C.TIER_1_MIN:g} L and above is Tier 1. For an exceptional brand or role, "
                              "the CMC can move an offer up one tier and must write down why."),
        ("Search the web", f"{len(C.SEARCH_PLAN)} searches per company: employee reviews on AmbitionBox and "
                           "Glassdoor, Reddit discussions, salary and interview reports, last year's news and the "
                           "company profile. Every source link is kept."),
        ("Read the sources", "Gemini reads the sources and FIIB reviews, and lists what people say. Each point "
                             "carries the sources that support it. Points with no source are thrown away."),
        ("Count, don't trust", f"The code counts separate sources for each point: {C.WIDELY_REPORTED_MIN_SOURCES} or "
                               "more from at least 2 different sites is widely reported, more than one is "
                               "repeated, and 1 is a single mention. Each review site counts as one site; "
                               "every news outlet counts separately."),
        ("Score and verdict", f"Package counts {int(w['package'] * 100)}%, brand {int(w['brand'] * 100)}%, role "
                              f"{int(w['role'] * 100)}% and work environment {int(w['environment'] * 100)}%. "
                              f"{C.RECOMMEND_MIN:g} and above is Recommend, {C.CAUTION_MIN:g} to {C.RECOMMEND_MIN:g} is "
                              f"Go with caution, below {C.CAUTION_MIN:g} is Avoid. A serious red flag from "
                              f"{C.RED_FLAG_CAP_SOURCES} or more sources holds a Recommend at caution."),
        ("Check student reviews", "One review per FIIB email per company. Reviews are flagged for copy-paste text, "
                                  "all-1 or all-5 ratings, very little detail or a sudden burst, and each one is "
                                  "checked against outside sources. Student reviews never change the score "
                                  "directly, and low-credibility ones are shown faded."),
    ]
    st.html("".join(f'<div class="pi-step"><div class="k">{i}</div><div><h4>{ui.esc(t)}</h4>'
                    f'<p>{ui.esc(d)}</p></div></div>' for i, (t, d) in enumerate(steps, 1)))
    st.caption("All these numbers live in core/config.py and can be changed in one place.")


# ------------------------------------------------------------------ navigation
st.html(ui.CSS)
st.logo(os.path.join(HERE, "static", "logo.svg"), size="large")
PAGES = {
    "companies": st.Page(page_companies, title="Companies", icon=":material/apartment:", url_path="companies",
                         default=True),
    "assess": st.Page(page_assess, title="New assessment", icon=":material/add_chart:", url_path="assess"),
    "review": st.Page(page_review, title="Share experience", icon=":material/rate_review:", url_path="review"),
    "panel": st.Page(page_panel, title="CMC panel", icon=":material/admin_panel_settings:", url_path="panel"),
    "method": st.Page(page_method, title="How it works", icon=":material/help:", url_path="how-it-works"),
}
st.navigation(list(PAGES.values()), position="top").run()
