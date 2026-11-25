"""HTML pieces for the app. Every piece of outside text goes through esc()."""
from __future__ import annotations

import html
from datetime import datetime

import config as C
from reviews import AI_MATCH, FLAG_TEXT, RATING_FIELDS, credibility

TIER_COLOR = {1: "var(--tier1)", 2: "var(--tier2)", 3: "var(--tier3)"}
VERDICT_CLASS = {"Recommend": "go", "Go with caution": "caution", "Avoid": "avoid"}
PLATFORM_CLASS = {"Reddit": "p-reddit", "AmbitionBox": "p-ambition", "Glassdoor": "p-glassdoor",
                  "News": "p-news", "Indeed": "p-indeed", "Naukri": "p-naukri", "LinkedIn": "p-linkedin"}

CSS = """
<style>
@import url("https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wdth,wght@12..96,75..100,200..800&family=Instrument+Sans:wght@400..700&display=swap");
:root{
  --ink:#171C3A; --ink-2:#4A5172; --ink-3:#7A81A0; --paper:#F3F5FA; --card:#FFFFFF; --line:#DCE1EE;
  --primary:#3340A0; --tier1:#7B3FC4; --tier2:#0D8FA3; --tier3:#64708C;
  --go:#1D9A5B; --caution:#D98B06; --avoid:#CF3646;
  --display:"Bricolage Grotesque",system-ui,sans-serif;
}
.block-container,[data-testid="stMainBlockContainer"]{max-width:1180px;padding-top:5rem;}
h1,h2,h3{letter-spacing:-0.02em;}
.pi-hero h1{font-family:var(--display);font-weight:750;font-size:clamp(2.1rem,4.2vw,3.3rem);
  line-height:1.02;margin:0 0 .5rem;color:var(--ink);font-variation-settings:"wdth" 88;}
.pi-hero p{color:var(--ink-2);font-size:1.08rem;max-width:62ch;margin:0;}
.pi-muted{color:var(--ink-3);font-size:.9rem;}
.pi-demo{display:inline-block;background:#FFF4D6;color:#8A5A00;border:1px solid #F1D48A;
  border-radius:999px;padding:.1rem .6rem;font-size:.78rem;font-weight:600;vertical-align:middle;}
.pi-banner{background:#FFF8E6;border:1px solid #F1D48A;color:#6B4A00;border-radius:.7rem;
  padding:.8rem 1rem;font-size:.95rem;margin:.4rem 0 1rem;}

/* ---------- tier chip and verdict chip ---------- */
.pi-tier{display:inline-flex;align-items:center;gap:.35rem;border-radius:999px;padding:.18rem .7rem;
  font-weight:650;font-size:.82rem;color:#fff;white-space:nowrap;}
.pi-tier.t1{background:var(--tier1);} .pi-tier.t2{background:var(--tier2);} .pi-tier.t3{background:var(--tier3);}
.pi-verdict{display:inline-block;border-radius:.45rem;padding:.2rem .6rem;font-weight:650;font-size:.85rem;}
.pi-verdict.go{background:#E2F5EA;color:#126B3E;} .pi-verdict.caution{background:#FDF0D7;color:#8C5800;}
.pi-verdict.avoid{background:#FBE4E6;color:#9E1F2C;}

/* ---------- package ruler (signature element) ---------- */
.pi-ruler{position:relative;margin:2.6rem 0 2.2rem;}
.pi-ruler .bands{display:flex;height:14px;border-radius:999px;overflow:hidden;}
.pi-ruler .band{height:100%;}
.pi-ruler .b3{background:linear-gradient(90deg,#C9CFDD,#8E98B0);}
.pi-ruler .b2{background:linear-gradient(90deg,#7CCAD6,#0D8FA3);}
.pi-ruler .b1{background:linear-gradient(90deg,#A97BE0,#7B3FC4);}
.pi-ruler .ticks{position:relative;height:1.4rem;margin-top:.35rem;font-size:.78rem;color:var(--ink-3);}
.pi-ruler .ticks span{position:absolute;transform:translateX(-50%);white-space:nowrap;}
.pi-ruler .bandname{position:absolute;top:-1.55rem;transform:translateX(-50%);font-size:.8rem;
  font-weight:650;white-space:nowrap;}
.pi-ruler .marker{position:absolute;top:-6px;width:26px;height:26px;margin-left:-13px;border-radius:50%;
  background:#fff;border:5px solid var(--ink);box-shadow:0 2px 8px rgba(23,28,58,.28);
  animation:pi-slide .9s cubic-bezier(.2,.8,.2,1) both;}
.pi-ruler .marker-label{position:absolute;top:-2.65rem;transform:translateX(-50%);background:var(--ink);
  color:#fff;font-family:var(--display);font-weight:700;font-size:.95rem;padding:.12rem .55rem;
  border-radius:.4rem;white-space:nowrap;animation:pi-fade .9s ease both;}
@keyframes pi-slide{from{left:0;}}
@keyframes pi-fade{from{opacity:0;}}

/* ---------- verdict panel ---------- */
.pi-verdict-panel{display:grid;grid-template-columns:auto 1fr;gap:1.6rem;align-items:center;
  background:var(--card);border:1px solid var(--line);border-radius:1rem;padding:1.4rem 1.6rem;}
.pi-verdict-panel .word{font-family:var(--display);font-weight:750;font-size:clamp(1.8rem,3.4vw,2.6rem);
  line-height:1;letter-spacing:-0.02em;}
.pi-verdict-panel.go .word{color:var(--go);} .pi-verdict-panel.caution .word{color:var(--caution);}
.pi-verdict-panel.avoid .word{color:var(--avoid);}
.pi-verdict-panel.go{border-left:6px solid var(--go);} .pi-verdict-panel.caution{border-left:6px solid var(--caution);}
.pi-verdict-panel.avoid{border-left:6px solid var(--avoid);}
.pi-verdict-panel .why{color:var(--ink-2);margin-top:.5rem;max-width:70ch;line-height:1.55;}
@property --p{syntax:"\\3c number\\3e";inherits:true;initial-value:0;}
.pi-dial,.pi-mini{position:relative;border-radius:50%;flex:none;}
.pi-dial{width:120px;height:120px;} .pi-mini{width:56px;height:56px;}
.pi-dial::before,.pi-mini::before{content:"";position:absolute;inset:0;border-radius:50%;
  background:conic-gradient(var(--c) calc(var(--p) * 1%), #E3E7F1 0);}
.pi-dial::before{-webkit-mask:radial-gradient(farthest-side,transparent calc(100% - 11px),#000 calc(100% - 10px));
  mask:radial-gradient(farthest-side,transparent calc(100% - 11px),#000 calc(100% - 10px));
  animation:pi-arc 1.1s cubic-bezier(.2,.8,.2,1) both;}
.pi-mini::before{-webkit-mask:radial-gradient(farthest-side,transparent calc(100% - 6px),#000 calc(100% - 5px));
  mask:radial-gradient(farthest-side,transparent calc(100% - 6px),#000 calc(100% - 5px));}
.pi-dial .num{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;
  justify-content:center;font-family:var(--display);}
.pi-dial .num b{font-size:2.1rem;font-weight:750;line-height:1;}
.pi-dial .num small{font-size:.75rem;color:var(--ink-3);}
@keyframes pi-arc{from{--p:0;}}

/* ---------- score bars ---------- */
.pi-bars{display:grid;gap:.9rem;}
.pi-bar .top{display:flex;justify-content:space-between;align-items:baseline;gap:1rem;}
.pi-bar .name{font-weight:650;} .pi-bar .w{color:var(--ink-3);font-size:.82rem;margin-left:.35rem;}
.pi-bar .val{font-family:var(--display);font-weight:700;}
.pi-bar .track{height:8px;background:#E3E7F1;border-radius:999px;margin:.3rem 0 .25rem;overflow:hidden;}
.pi-bar .fill{height:100%;border-radius:999px;background:var(--primary);}
.pi-bar .reason{color:var(--ink-2);font-size:.9rem;line-height:1.45;}

/* ---------- claims ---------- */
.pi-group-title{font-family:var(--display);font-weight:700;font-size:1.1rem;margin:1.2rem 0 .15rem;}
.pi-group-note{color:var(--ink-3);font-size:.88rem;margin-bottom:.55rem;}
.pi-claim{display:grid;grid-template-columns:10px 1fr auto;gap:.85rem;align-items:start;background:var(--card);
  border:1px solid var(--line);border-radius:.7rem;padding:.8rem 1rem;margin-bottom:.5rem;}
.pi-claim.single{background:transparent;border-style:dashed;}
.pi-claim .dot{width:10px;height:10px;border-radius:50%;margin-top:.45rem;}
.pi-claim .dot.positive{background:var(--go);} .pi-claim .dot.negative{background:var(--avoid);}
.pi-claim .dot.mixed{background:var(--caution);}
.pi-claim .topic{font-size:.8rem;color:var(--ink-3);font-weight:600;}
.pi-claim .stmt{font-size:1rem;line-height:1.45;}
.pi-claim .srcs{display:flex;flex-wrap:wrap;gap:.3rem;margin-top:.45rem;}
.pi-count{font-family:var(--display);font-weight:700;text-align:right;line-height:1.1;white-space:nowrap;}
.pi-count small{display:block;font-family:inherit;font-weight:500;color:var(--ink-3);font-size:.72rem;}
.pi-src{display:inline-block;text-decoration:none!important;border-radius:.35rem;padding:.08rem .45rem;
  font-size:.76rem;font-weight:600;border:1px solid transparent;}
.pi-src:hover{filter:brightness(.95);}
.p-reddit{background:#FFE9DF;color:#B23C0B!important;} .p-ambition{background:#E4F0FF;color:#1D4F9E!important;}
.p-glassdoor{background:#E0F5E6;color:#1B6B37!important;} .p-news{background:#EFE9FB;color:#5A2CA0!important;}
.p-indeed{background:#E3E8FF;color:#2A3A9E!important;} .p-naukri{background:#E3F4FA;color:#0B6F8A!important;}
.p-linkedin{background:#E1EEF9;color:#0A5BA8!important;} .p-web{background:#EEF0F5;color:#454C6A!important;}
.pi-fiib{display:inline-block;font-size:.76rem;font-weight:600;color:var(--primary);background:#E8EAF8;
  border-radius:.35rem;padding:.08rem .45rem;}

/* ---------- ratings strip ---------- */
.pi-ratings{display:flex;flex-wrap:wrap;gap:.6rem;margin:.4rem 0 .6rem;}
.pi-rating{background:var(--card);border:1px solid var(--line);border-radius:.7rem;padding:.55rem .85rem;min-width:9rem;}
.pi-rating b{font-family:var(--display);font-size:1.45rem;font-weight:750;}
.pi-rating span{color:var(--ink-3);font-size:.8rem;}

/* ---------- flags ---------- */
.pi-flag{display:flex;gap:.7rem;align-items:flex-start;padding:.7rem .9rem;border-radius:.65rem;margin-bottom:.45rem;}
.pi-flag.high{background:#FBE4E6;} .pi-flag.medium{background:#FDF0D7;} .pi-flag.low{background:#EEF0F5;}
.pi-flag .sev{font-weight:700;font-size:.78rem;border-radius:.3rem;padding:.05rem .4rem;color:#fff;white-space:nowrap;}
.pi-flag.high .sev{background:var(--avoid);} .pi-flag.medium .sev{background:var(--caution);}
.pi-flag.low .sev{background:var(--tier3);}

/* ---------- review card ---------- */
.pi-review{background:var(--card);border:1px solid var(--line);border-radius:.8rem;padding:1rem 1.1rem;margin-bottom:.6rem;}
.pi-review.low{opacity:.72;border-style:dashed;}
.pi-review .head{display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap;margin-bottom:.4rem;}
.pi-review .who{font-weight:650;} .pi-review .when{color:var(--ink-3);font-size:.85rem;}
.pi-cred{font-size:.78rem;font-weight:650;border-radius:999px;padding:.15rem .65rem;align-self:flex-start;line-height:1.4;white-space:nowrap;}
.pi-cred.high{background:#E2F5EA;color:#126B3E;} .pi-cred.medium{background:#FDF0D7;color:#8C5800;}
.pi-cred.low{background:#FBE4E6;color:#9E1F2C;}
.pi-stars{color:#E3A008;letter-spacing:.05em;} .pi-stars i{color:#D5D9E5;font-style:normal;}
.pi-review dl{display:grid;grid-template-columns:5.5rem 1fr;gap:.25rem .8rem;margin:.6rem 0 .2rem;}
.pi-review dt{color:var(--ink-3);font-size:.88rem;} .pi-review dd{margin:0;line-height:1.45;}
.pi-review .check{font-size:.88rem;color:var(--ink-2);border-top:1px solid var(--line);padding-top:.5rem;margin-top:.5rem;}

/* ---------- company ledger rows ---------- */
.pi-row{display:grid;grid-template-columns:64px minmax(0,1.6fr) minmax(0,1fr) minmax(0,1fr);gap:1.1rem;
  align-items:center;background:var(--card);border:1px solid var(--line);border-radius:.85rem;
  padding:.8rem 1.1rem;border-left:6px solid var(--tc);}
.pi-row .name{font-family:var(--display);font-weight:700;font-size:1.18rem;line-height:1.15;}
.pi-row .role{color:var(--ink-2);font-size:.92rem;}
.pi-row .ctc{font-family:var(--display);font-weight:700;font-size:1.15rem;}
.pi-mini b{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  font-family:var(--display);font-weight:750;font-size:1.05rem;}
.pi-stats{display:flex;flex-wrap:wrap;gap:2rem;margin:1.4rem 0 1.2rem;padding:1rem 0;border-top:1px solid var(--line);
  border-bottom:1px solid var(--line);}
.pi-stat b{display:block;font-family:var(--display);font-weight:750;font-size:1.7rem;line-height:1.1;}
.pi-stat span{color:var(--ink-3);font-size:.85rem;}

/* ---------- source list ---------- */
.pi-source{padding:.75rem 0;border-bottom:1px solid var(--line);}
.pi-source a.t{font-weight:650;color:var(--ink)!important;text-decoration:none;}
.pi-source a.t:hover{text-decoration:underline;}
.pi-source p{margin:.25rem 0 0;color:var(--ink-2);font-size:.92rem;line-height:1.45;}
.pi-source .n{color:var(--ink-3);font-size:.8rem;margin-right:.4rem;}

/* ---------- method page ---------- */
.pi-step{display:grid;grid-template-columns:2.2rem 1fr;gap:.9rem;margin-bottom:1rem;}
.pi-step .k{width:2.2rem;height:2.2rem;border-radius:50%;background:var(--ink);color:#fff;display:flex;
  align-items:center;justify-content:center;font-family:var(--display);font-weight:700;}
.pi-step h4{margin:.15rem 0 .2rem;font-family:var(--display);}
.pi-step p{margin:0;color:var(--ink-2);line-height:1.5;}

@media (max-width:760px){
  .pi-row{grid-template-columns:56px 1fr;}
  .pi-row .c3,.pi-row .c4{grid-column:2;}
  .pi-verdict-panel{grid-template-columns:1fr;}
}
@media (prefers-reduced-motion:reduce){
  .pi-ruler .marker,.pi-ruler .marker-label,.pi-dial::before{animation:none;}
}
</style>
"""


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def safe_url(u: str) -> str:
    u = str(u or "")
    return esc(u) if u.startswith(("http://", "https://")) else "#"


def fmt_lpa(v: float) -> str:
    return f"₹{v:g} L"


def fmt_date(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d %b %Y")
    except (TypeError, ValueError):
        return ""


def tier_chip(tier: int, override: bool = False) -> str:
    extra = " (moved up)" if override else ""
    return f'<span class="pi-tier t{tier}">Tier {tier}{extra}</span>'


def verdict_chip(verdict: str) -> str:
    return f'<span class="pi-verdict {VERDICT_CLASS.get(verdict, "caution")}">{esc(verdict)}</span>'


def _verdict_color(verdict: str) -> str:
    return {"Recommend": "var(--go)", "Go with caution": "var(--caution)", "Avoid": "var(--avoid)"}.get(
        verdict, "var(--primary)")


def mini_dial(score: float, verdict: str) -> str:
    return (f'<div class="pi-mini" style="--p:{score * 10:.0f};--c:{_verdict_color(verdict)}">'
            f'<b>{score:.1f}</b></div>')


def dial(score: float, verdict: str) -> str:
    return (f'<div class="pi-dial" style="--p:{score * 10:.0f};--c:{_verdict_color(verdict)}">'
            f'<div class="num"><b>{score:.1f}</b><small>out of 10</small></div></div>')


RULER_MAX = 25.0


def ruler(ctc: float | None) -> str:
    def pos(v):
        return min(100.0, max(0.0, v / RULER_MAX * 100))

    p10, p15 = pos(C.TIER_2_MIN), pos(C.TIER_1_MIN)
    bands = (f'<div class="bands"><div class="band b3" style="width:{p10}%"></div>'
             f'<div class="band b2" style="width:{p15 - p10}%"></div>'
             f'<div class="band b1" style="width:{100 - p15}%"></div></div>')
    names = (f'<span class="bandname" style="left:{p10 / 2}%;color:var(--tier3)">Tier 3</span>'
             f'<span class="bandname" style="left:{(p10 + p15) / 2}%;color:var(--tier2)">Tier 2</span>'
             f'<span class="bandname" style="left:{(p15 + 100) / 2}%;color:var(--tier1)">Tier 1</span>')
    ticks = "".join(f'<span style="left:{pos(v)}%">{lab}</span>'
                    for v, lab in [(0, "₹0"), (6, "₹6 L"), (10, "₹10 L"), (15, "₹15 L"), (20, "₹20 L"),
                                   (25, "₹25 L+")])
    ticks = ticks.replace('style="left:0.0%"', 'style="left:0%;transform:none"').replace(
        'style="left:100.0%"', 'style="left:100%;transform:translateX(-100%)"')
    marker = ""
    if ctc is not None and ctc > 0:
        p = pos(ctc)
        lp = min(94.0, max(6.0, p))
        marker = (f'<div class="marker" style="left:{p}%"></div>'
                  f'<div class="marker-label" style="left:{lp}%">{fmt_lpa(ctc)}</div>')
    if marker:
        names = ""  # the label sits where the band names would; band colours still say it all
    return f'<div class="pi-ruler">{names}{bands}{marker}<div class="ticks">{ticks}</div></div>'


def verdict_panel(a: dict) -> str:
    cls = VERDICT_CLASS.get(a["verdict"], "caution")
    cap = ""
    if a.get("verdict_capped_by"):
        cap = (f'<div class="pi-muted" style="margin-top:.5rem">The score alone says Recommend, but this '
               f'red flag holds it at caution: {esc(a["verdict_capped_by"])}</div>')
    return (f'<div class="pi-verdict-panel {cls}">{dial(a["score"], a["verdict"])}<div>'
            f'<div class="word">{esc(a["verdict"])}</div>'
            f'<div class="why">{esc(a.get("summary", ""))}</div>{cap}</div></div>')


def score_bars(a: dict) -> str:
    s = a["scores"]
    rows = [
        ("package", "Package", f"{fmt_lpa(a['ctc_lpa'])} total CTC, {C.TIER_INFO[a['base_tier']]['name']}"),
        ("brand", "Brand", a.get("brand_reason", "")),
        ("role", "Role", a.get("role_reason", "")),
        ("environment", "Work environment", a.get("environment_reason", "")),
    ]
    out = []
    for k, name, reason in rows:
        v = float(s.get(k, 0))
        out.append(
            f'<div class="pi-bar"><div class="top"><div><span class="name">{name}</span>'
            f'<span class="w">counts {int(C.WEIGHTS[k] * 100)}%</span></div><span class="val">{v:.1f}</span></div>'
            f'<div class="track"><div class="fill" style="width:{v * 10}%"></div></div>'
            f'<div class="reason">{esc(reason)}</div></div>')
    return f'<div class="pi-bars">{"".join(out)}</div>'


def chip_label(s: dict) -> str:
    """Review sites show their name; news and other sites show the outlet, e.g. livemint.com."""
    if s.get("platform") in ("News", "Web"):
        from rules import domain_of
        return domain_of(s.get("url", "")) or s["platform"]
    return s["platform"]


def src_chips(ids: list[int], sources: list[dict]) -> str:
    chips = []
    for i in ids:
        if 0 <= i < len(sources):
            s = sources[i]
            cls = PLATFORM_CLASS.get(s["platform"], "p-web")
            chips.append(f'<a class="pi-src {cls}" href="{safe_url(s["url"])}" target="_blank" '
                         f'rel="noopener" title="{esc(s["title"])}">{esc(chip_label(s))}</a>')
    return "".join(chips)


def claim_card(c: dict, sources: list[dict]) -> str:
    cons = c["consensus"]
    fiib = ""
    if c.get("fiib_review_ids"):
        n = len(c["fiib_review_ids"])
        fiib = f'<span class="pi-fiib">Also said by {n} FIIB review{"s" if n > 1 else ""}</span>'
    unit = "source" if cons["sources"] == 1 else "sources"
    single = " single" if cons["level"] == "single" else ""
    return (f'<div class="pi-claim{single}"><span class="dot {esc(c["sentiment"])}"></span><div>'
            f'<div class="topic">{esc(c["topic"])}</div><div class="stmt">{esc(c["statement"])}</div>'
            f'<div class="srcs">{src_chips(c["source_ids"], sources)}{fiib}</div></div>'
            f'<div class="pi-count">{cons["sources"]}<small>{unit}</small></div></div>')


GROUP_NOTES = {
    "wide": ("Widely reported", "Said by 3 or more separate sources from at least 2 different sites."),
    "repeated": ("Repeated", "Said by more than one source, but not yet widely across different sites."),
    "single": ("Single mention", "Only one source says this. It may be true, but treat it as one "
                                 "person's experience until others confirm it."),
}


def claims_html(a: dict) -> str:
    out = []
    for level, (title, note) in GROUP_NOTES.items():
        group = [c for c in a["claims"] if c["consensus"]["level"] == level]
        if not group:
            continue
        out.append(f'<div class="pi-group-title">{title}</div><div class="pi-group-note">{note}</div>')
        out += [claim_card(c, a["sources"]) for c in group]
    return "".join(out) or '<p class="pi-muted">No supported claims were found.</p>'


def ratings_html(a: dict) -> str:
    if not a.get("external_ratings"):
        return ""
    tiles = []
    for r in a["external_ratings"]:
        based = f" from {esc(r['based_on'])}" if r.get("based_on") else ""
        tiles.append(f'<div class="pi-rating"><b>{r["rating"]:.1f}</b><span> / {r["out_of"]:g}</span><br>'
                     f'<span>{esc(r["platform"])}{based}</span></div>')
    return f'<div class="pi-ratings">{"".join(tiles)}</div>'


def flags_html(a: dict) -> str:
    if not a.get("red_flags"):
        return '<p class="pi-muted">No red flags were found in the sources.</p>'
    out = []
    for f in a["red_flags"]:
        sev = f.get("severity", "medium")
        chips = src_chips(f.get("source_ids", []), a["sources"])
        out.append(f'<div class="pi-flag {esc(sev)}"><span class="sev">{esc(sev.capitalize())}</span>'
                   f'<div>{esc(f["flag"])}<div class="srcs" style="margin-top:.3rem">{chips}</div></div></div>')
    return "".join(out)


def stars(n: int) -> str:
    n = max(0, min(5, int(n or 0)))
    return f'<span class="pi-stars" aria-label="{n} out of 5">{"★" * n}<i>{"★" * (5 - n)}</i></span>'


def review_card(r: dict) -> str:
    cred = credibility(r)
    flags = [FLAG_TEXT[f] for f in (r.get("flags") or []) if f in FLAG_TEXT]
    check = ""
    if r.get("ai_match") in AI_MATCH:
        check = f'<div class="check"><b>{AI_MATCH[r["ai_match"]][0]}.</b> {esc(r.get("ai_note", ""))}</div>'
    if flags:
        check += f'<div class="check">Flagged: {esc(", ".join(flags))}.</div>'
    rows = "".join(f"<dt>{label}</dt><dd>{esc(r.get(k))}</dd>"
                   for k, label in (("pros", "Liked"), ("cons", "Disliked"), ("interview", "Interview"))
                   if str(r.get(k) or "").strip())
    sub = ", ".join(x for x in (esc(r.get("role")), esc(r.get("relation")), esc(r.get("year"))) if x)
    return (f'<div class="pi-review {cred["level"]}"><div class="head"><div><div class="who">{sub}</div>'
            f'<div class="when">{stars(r.get("rating_overall"))} posted {fmt_date(r.get("created_at", ""))}</div>'
            f'</div><span class="pi-cred {cred["level"]}">{cred["label"]}</span></div>'
            f'<dl>{rows}</dl>{check}</div>')


def sources_html(a: dict) -> str:
    out = []
    for i, s in enumerate(a["sources"]):
        cls = PLATFORM_CLASS.get(s["platform"], "p-web")
        date = f' <span class="pi-muted">{esc(s["published"])}</span>' if s.get("published") else ""
        out.append(f'<div class="pi-source"><span class="n">{i}</span><span class="pi-src {cls}">'
                   f'{esc(s["platform"])}</span> <a class="t" href="{safe_url(s["url"])}" target="_blank" '
                   f'rel="noopener">{esc(s["title"])}</a>{date}<p>{esc(s["snippet"])}</p></div>')
    return "".join(out) or '<p class="pi-muted">No sources.</p>'


def company_row(a: dict) -> str:
    tc = TIER_COLOR[a["tier"]]
    demo = ' <span class="pi-demo">Sample</span>' if a.get("demo") else ""
    loc = f", {esc(a['location'])}" if a.get("location") else ""
    return (f'<div class="pi-row" style="--tc:{tc}">{mini_dial(a["score"], a["verdict"])}'
            f'<div><div class="name">{esc(a["company"])}{demo}</div><div class="role">{esc(a["role"])}{loc}</div></div>'
            f'<div class="c3"><div class="ctc">{fmt_lpa(a["ctc_lpa"])}</div>{tier_chip(a["tier"], a.get("override"))}</div>'
            f'<div class="c4">{verdict_chip(a["verdict"])}<div class="pi-muted" style="margin-top:.3rem">'
            f'Assessed {fmt_date(a["created_at"])}</div></div></div>')


def rating_fields():
    return RATING_FIELDS
