"""Weekly cattle market news, one page per state (market news step 2; Scott chose the Nebraska layout "As drawn",
notes/nebraska-markets-computer/phone-2026-10-14.png).

Every Friday the weekly job saves, with each barn's price sheet, USDA's report of that barn's latest sale (Herd Planner
v0.48+ sends it in /suite/barns; cards.record_barns keeps it in content/cards/barns.json). From those this module
writes, for each state in STATES:

- markets-ne.html: the newest week, rewritten every Friday;
- markets-ne-2026-w42.html: one page per week, which never changes once the week is over. Those dated pages are the
  growing record search engines see; each page lists the earlier weeks.

What a page says, and where each part comes from:

- The opening line is made by rules from the newest sale's numbers (head sold, against USDA's own week-ago and year-ago
  counts) and quotes USDA's one-line summary as written. Every word follows from USDA's report.
- Tiles: head sold at the barns' latest sales; Herd Planner's 550 lb steer estimate across those barns (labelled as
  ours); and the next sale dates when USDA's reporter names them ("Next Auction Date Oct 16th ..."), from the day the
  page is written on (a Friday sale is still ahead at 7 am). Without one, how many of the state's barns reported.
- A card for each barn that sold in the last three weeks, newest first: head sold, our estimate, the reporter's
  narrative in USDA's own words (public domain, 17 U.S.C. 105), and the link to the report.
- A barn without a fresh sale gets one quiet line ("no sale reported since ...") instead of a stale price.

Head counts are neutral: more cattle isn't good or bad, so their arrows are never red. A state gets a page for a week
only when at least one of its barns has a fresh sale with a USDA report that week (thin pages hurt a site in search).
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from html import escape

STATES = {"NE": "Nebraska"}  # Scott, 2026-10-12: Nebraska first; Iowa once Herd Planner follows Iowa barns
WEIGHT = 550
EARLIER_SHOWN = 8  # earlier weeks listed as buttons; the rest fold under "More Weeks"
MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}


def e(x) -> str:
    return escape(str(x), quote=True)


def money(x: float) -> str:
    return f"${x:,.0f}"


def short(d: date) -> str:
    return f"{d:%b} {d.day}"


def day_words(d: date) -> str:
    """Tue, Oct 13"""
    return f"{d:%a}, {d:%b} {d.day}"


def monday(iso_week: str) -> date:
    """2026-W42 -> the Monday that starts it (Oct 12, 2026)."""
    year, week = iso_week.split("-W")
    return date.fromisocalendar(int(year), int(week), 1)


def page_name(state: str, week: str | None = None) -> str:
    """markets-ne.html (the newest week) or markets-ne-2026-w42.html (one week, kept as it was)."""
    return f"markets-{state.lower()}" + (f"-{week.lower()}" if week else "") + ".html"


def clean(text: str | None) -> str:
    """USDA's words as written, minus the report's internal markers ("*** Add Close ***") and doubled spaces."""
    text = re.sub(r"\*{2,}[^*]*\*{2,}", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def price_at(week: dict, cls: str = "Steers", weight: int = WEIGHT) -> dict | None:
    return next((p for p in week.get("prices", []) if p["animal_class"] == cls and p["weight_lb"] == weight), None)


def change(now: int, then: int | None, when: str) -> str:
    """'<b>▼ 16%</b> fewer than a week before (1,132)'. Head counts are neutral: no red, the arrow comes with words."""
    if not then:
        return f"No sale {when}"
    pct = round(100 * (now / then - 1))
    if pct == 0:
        return f"About the same as {when} ({then:,})"
    arrow, words = ("▲", "more") if pct > 0 else ("▼", "fewer")
    return f'<b><span aria-hidden="true">{arrow}</span> {abs(pct)}%</b> {words} than {when} ({then:,})'


def next_sale(report: dict) -> date | None:
    """The first date after "Next Auction Date(s)" / "Next Sale Date" in the reporter's narrative, if there is one
    ("Next Auction Date Oct 16th 23rd & 30th ..." -> Oct 16). A month before the sale's month is next year."""
    m = re.search(r"Next\s+(?:Auction|Sale)\s+Dates?\s*:?\s*([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b",
                  report.get("narrative") or "", re.I)
    sold = report.get("sale_date")
    if not m or not sold or m.group(1)[:3].lower() not in MONTHS:
        return None
    sold = date.fromisoformat(sold)
    month, day = MONTHS[m.group(1)[:3].lower()], int(m.group(2))
    try:
        when = date(sold.year + (1 if month < sold.month else 0), month, day)
    except ValueError:  # "Feb 30th": not a date
        return None
    return when if when > sold else None


# --- which barns, which weeks ------------------------------------------------------------------------------------

def week_rows(barns: dict, state: str, week: str) -> tuple[list[dict], list[dict]]:
    """(sold, quiet) for one state and week. sold: the barns whose sheet that week is fresh and carries USDA's report,
    newest sale first. quiet: the state's other barns with that week's (or their latest) last sale."""
    sold, quiet = [], []
    for slug, b in barns.items():
        if b.get("state") != state:
            continue
        entry = next((w for w in b.get("weeks", []) if w["week"] == week), None)
        report = (entry or {}).get("report")
        if entry and entry.get("fresh") and report and report.get("head_sold") is not None and report.get("sale_date"):
            sold.append({"slug": slug, "barn": b, "entry": entry, "report": report,
                         "sale": date.fromisoformat(report["sale_date"])})
        else:
            latest = entry or next((w for w in b.get("weeks", []) if w["week"] <= week), None)
            quiet.append({"slug": slug, "barn": b, "last_sale": (latest or {}).get("last_sale"),
                          "fresh": bool(latest and latest.get("fresh"))})
    sold.sort(key=lambda r: (r["sale"], r["barn"]["name"]), reverse=True)
    quiet.sort(key=lambda r: r["barn"].get("city") or r["barn"]["name"])
    return sold, quiet


def weeks_with_news(barns: dict, state: str) -> list[str]:
    """Every week (newest first) in which the state had at least one fresh sale with USDA's report."""
    ids = {w["week"] for b in barns.values() if b.get("state") == state for w in b.get("weeks", [])}
    return sorted((wk for wk in ids if week_rows(barns, state, wk)[0]), reverse=True)


# --- the page ----------------------------------------------------------------------------------------------------

def lede(top: dict, state_name: str) -> str:
    """The opening line, by rules from the newest sale: head sold against USDA's own week-ago and year-ago counts,
    then the reporter's one-line summary as written (when it is a line, not a paragraph)."""
    r, b = top["report"], top["barn"]
    town = b.get("city") or b["name"]
    said = []
    for then, when in ((r.get("head_week_ago"), "the week before"), (r.get("head_year_ago"), "a year ago")):
        if then:
            pct = round(100 * (r["head_sold"] / then - 1))
            said.append(f"about the same as {when}" if pct == 0 else f"{abs(pct)}% {'more' if pct > 0 else 'fewer'} than {when}")
    text = f"{e(town)} sold {r['head_sold']:,} head on {e(day_words(top['sale']))}"
    if said:
        text += ", " + " and ".join(said)
    text += "."
    summary = clean(r.get("summary"))
    if summary and len(summary) <= 220:
        text += f" USDA&rsquo;s market reporter: &ldquo;{e(summary)}&rdquo;"
    return text


def tiles(sold: list[dict], quiet: list[dict], state_name: str, built: date) -> str:
    head = sum(r["report"]["head_sold"] for r in sold)
    first, last = min(r["sale"] for r in sold), max(r["sale"] for r in sold)
    where = (f"At {len(sold)} {e(state_name)} barns, {short(first)} to {short(last)}" if len(sold) > 1 else
             f"At {e(sold[0]['barn'].get('city') or sold[0]['barn']['name'])}, {short(last)}")
    steers = [(r, price_at(r["entry"])) for r in sold]
    steers = [(r, p) for r, p in steers if p]
    if steers:
        lo, hi = min(p["price"] for _, p in steers), max(p["price"] for _, p in steers)
        big = f"{money(lo)}&ndash;{money(hi)}" if round(lo) != round(hi) else money(lo)
        per_head = (f"About {money(lo * WEIGHT / 100)} to {money(hi * WEIGHT / 100)} a head" if round(lo) != round(hi)
                    else f"About {money(lo * WEIGHT / 100)} a head")
        across = f"Across those {len(steers)} barns" if len(steers) > 1 else f"At {e(steers[0][0]['barn'].get('city') or steers[0][0]['barn']['name'])}"
        price_tile = f"""<div class="news-tile"><p class="lbl">550 lb steer, our estimate</p><p class="big">{big}<small>/cwt</small></p>
        <p class="chg">{across}<br>{per_head}</p></div>"""
    else:
        price_tile = ""
    coming = sorted(((d, r) for r in sold for d in [next_sale(r["report"])] if d and d >= built), key=lambda x: x[0])[:2]
    if coming:
        days = " &middot; ".join(short(d) for d, _ in coming)
        lines = "<br>".join(f"{e(r['barn'].get('city') or r['barn']['name'])}, {d:%a}" for d, r in coming)
        third = f"""<div class="news-tile"><p class="lbl">Next sales, per USDA&rsquo;s reports</p><p class="big">{days}</p>
        <p class="chg">{lines}</p></div>"""
    else:
        total = len(sold) + len(quiet)
        third = f"""<div class="news-tile"><p class="lbl">Barns reporting</p><p class="big">{len(sold)} of {total}</p>
        <p class="chg">{e(state_name)} barns with a sale in the last three weeks</p></div>"""
    return f"""<div class="news-tiles">
      <div class="news-tile"><p class="lbl">Head sold, latest sales</p><p class="big">{head:,}</p><p class="chg">{where}</p></div>
      {price_tile}
      {third}
    </div>"""


def barn_card(r: dict, barn_href) -> str:
    rep, b = r["report"], r["barn"]
    href = barn_href(r["slug"])
    name = f'<a href="{e(href)}">{e(b["name"])}</a>' if href else e(b["name"])
    p = price_at(r["entry"])
    est = (f"""<div><p class="lbl">550 lb steer, our estimate</p><p class="big">{money(p['price'])}<small>/cwt</small></p>
          <p class="chg">About {money(p['price'] * WEIGHT / 100)} a head{f'<br><a href="{e(href)}">Price sheet &rsaquo;</a>' if href else ''}</p></div>"""
           if p else "")
    words = clean(rep.get("narrative")) or clean(rep.get("summary"))
    quote = f'<blockquote class="reporter"><p>{e(words)}</p></blockquote>' if words else ""
    link = f' <a href="{e(rep["url"])}" rel="noopener">Read USDA&rsquo;s report &rsaquo;</a>' if rep.get("url") else ""
    prelim = "" if rep.get("final", True) else " Preliminary: USDA may still revise it."
    section = clean(rep.get("section")) or "auction"
    return f"""<article class="barn-news">
      <div class="bn-head"><h3>{name}</h3><p class="bn-date">{e(day_words(r['sale']))}</p></div>
      <div class="bn-figs">
        <div><p class="lbl">Head sold</p><p class="big">{rep['head_sold']:,}</p>
          <p class="chg">{change(rep['head_sold'], rep.get('head_week_ago'), 'a week before')}<br>{change(rep['head_sold'], rep.get('head_year_ago'), 'a year before')}</p></div>
        {est}
      </div>
      {quote}
      <p class="cite">USDA AMS Market News, {e(b['name'])} {e(section)}, {e(short(r['sale']))}, {r['sale'].year}, in USDA&rsquo;s own words.{prelim}{link}</p>
    </article>"""


def quiet_line(q: dict, barn_href) -> str:
    href = barn_href(q["slug"])
    name = f'<a href="{e(href)}">{e(q["barn"]["name"])}</a>' if href else e(q["barn"]["name"])
    if q.get("last_sale") and q.get("fresh"):  # sold, but no USDA report came with it (an older Herd Planner)
        d = date.fromisoformat(q["last_sale"])
        when = f"sold on {e(day_words(d))}; USDA&rsquo;s report of that sale isn&rsquo;t in our data"
    elif q.get("last_sale"):
        d = date.fromisoformat(q["last_sale"])
        when = f"no sale reported in the last three weeks; its last in our data was {e(day_words(d))}, {d.year}"
    else:
        when = "no sale reported yet"
    return f"<li><b>{name}</b>: {when}.</li>"


def state_page(state: str, week: str, barns: dict, barn_href, weeks: list[str]) -> tuple[str, str, str]:
    """(title, description, body) for one state's page for one week."""
    name = STATES[state]
    sold, quiet = week_rows(barns, state, week)
    start = monday(week)
    built = max(date.fromisoformat(r["entry"]["date"]) for r in sold)
    title = f"{name} Cattle Markets: Week of {short(start)}, {start.year}"
    top = sold[0]
    desc = (f"{name} feeder cattle sales, week of {short(start)}, {start.year}: "
            f"{top['barn'].get('city') or top['barn']['name']} sold {top['report']['head_sold']:,} head on "
            f"{short(top['sale'])}. Head sold, USDA's market reports and our 550 lb steer estimate at each barn.")
    cards = "\n    ".join(barn_card(r, barn_href) for r in sold)
    quiet_html = (f'<ul class="plain market-quiet">{"".join(quiet_line(q, barn_href) for q in quiet)}</ul>' if quiet else "")
    earlier = [w for w in weeks if w < week]
    if earlier:
        chips = lambda ws: "".join(f'<a href="{page_name(state, w)}">Week of {short(monday(w))}</a>' for w in ws)
        more = (f'<details class="more-weeks"><summary>More Weeks</summary><div class="weeks">{chips(earlier[EARLIER_SHOWN:])}</div></details>'
                if len(earlier) > EARLIER_SHOWN else "")
        earlier_html = f'<h2>Earlier Weeks</h2>\n    <div class="weeks">{chips(earlier[:EARLIER_SHOWN])}</div>{more}'
    else:
        earlier_html = ""
    body = f"""<section class="page market-page">
  <div class="wrap">
    <p class="eyebrow"><a href="barns.html">Barn Prices</a> &rsaquo; {e(name)} Markets</p>
    <h1>{e(name)} Cattle Markets: Week of {short(start)}</h1>
    <p class="lede">{lede(top, name)}</p>
    {tiles(sold, quiet, name, built)}
    <h2>Latest Sale at Each Barn</h2>
    {cards}
    {quiet_html}
    {earlier_html}
    <p class="note">Written every Friday from USDA AMS Market News auction reports (public domain). Head counts and
      USDA&rsquo;s words are as reported; the 550 lb steer is Herd Planner&rsquo;s estimate, not a quote
      (<a href="methods.html#herd-planner">how we test it</a>). This week&rsquo;s page is saved as it is, and saved
      weeks never change.</p>
  </div>
</section>"""
    return title, desc, body


def pages(barns: dict, barn_href) -> list[tuple[str, str, str, str, str]]:
    """[(file name, title, description, body, state)] for every state and week with news; the newest week also as
    markets-xx.html."""
    out = []
    for state in STATES:
        weeks = weeks_with_news(barns, state)
        for i, wk in enumerate(weeks):
            title, desc, body = state_page(state, wk, barns, barn_href, weeks)
            out.append((page_name(state, wk), title, desc, body, state))
            if i == 0:
                out.append((page_name(state), title, desc, body, state))
    return out


def index_links(barns: dict) -> str:
    """Barn Prices' "This Week's Markets" section (Scott, 2026-10-13): a link to each state's newest page."""
    rows = []
    for state, name in STATES.items():
        weeks = weeks_with_news(barns, state)
        if weeks:
            rows.append(f'<li><a href="{page_name(state)}">{e(name)} Cattle Markets</a>, week of '
                        f'{short(monday(weeks[0]))}: head sold and USDA&rsquo;s market reports at each barn</li>')
    if not rows:
        return ""
    return f"""    <h2>This Week&rsquo;s Markets</h2>
    <ul class="plain market-links">{"".join(rows)}</ul>
"""
