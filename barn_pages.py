"""One page per sale barn, plus an index of them all ("Barn Prices").

Each page answers the question a rancher actually searches for: "what are feeder cattle bringing at
<town> this week?" From content/cards/barns.json (the Friday job saves Herd Planner's price sheet for
every barn it has prices for), each page shows:

- this week's 550 lb steer price and its range, with the change from last week (same barn, so the
  weeks compare; red only when the price fell, always with an arrow and words),
- a price sheet: steers and heifers at 400 to 800 lb, $/cwt and $ a head, with ranges,
- the last 12 weeks as a chart (a dot per week, a whisker for the range),
- other barns in the same state, and how the numbers are worked out.

A barn that hasn't sold in three weeks keeps its page (and its history) but says so instead of
showing a stale price as "this week".
"""

from __future__ import annotations

import re
from datetime import date
from html import escape

import charts
import hero

WEIGHT = 550
HISTORY_WEEKS = 12
STATE_NAMES = {"NE": "Nebraska", "IA": "Iowa", "KS": "Kansas", "SD": "South Dakota", "CO": "Colorado",
               "WY": "Wyoming", "MO": "Missouri", "OK": "Oklahoma", "TX": "Texas", "MT": "Montana"}


def e(x) -> str:
    return escape(str(x), quote=True)


def money(x: float) -> str:
    return f"${x:,.0f}"


def page_name(slug: str, barn: dict) -> str:
    """barn-kearney-ne-1848.html: the town in the address (people search by town), the USDA report
    number at the end so two sales in one town never collide."""
    town = re.sub(r"[^a-z0-9]+", "-", f'{barn.get("city") or barn["name"]} {barn.get("state") or ""}'.lower()).strip("-")
    return f"barn-{town}-{slug}.html"


def place(barn: dict) -> str:
    return ", ".join(x for x in (barn.get("city"), barn.get("state")) if x)


def price_at(week: dict, cls: str, weight: int) -> dict | None:
    return next((p for p in week["prices"] if p["animal_class"] == cls and p["weight_lb"] == weight), None)


def current(barn: dict) -> dict | None:
    """This week's sheet, or None when the barn hasn't sold in three weeks."""
    weeks = barn.get("weeks") or []
    return weeks[0] if weeks and weeks[0]["fresh"] else None


def change_flag(barn: dict) -> str:
    """The 550 lb steer price against last week's, at this same barn."""
    weeks = barn.get("weeks") or []
    if len(weeks) < 2 or not weeks[0]["fresh"] or not weeks[1]["fresh"]:
        return ""
    now, before = price_at(weeks[0], "Steers", WEIGHT), price_at(weeks[1], "Steers", WEIGHT)
    if not now or not before:
        return ""
    diff = round(now["price"]) - round(before["price"])
    if diff == 0:
        return ' <span class="badge up">no change from last week</span>'
    return hero.badge(f"{money(abs(diff))} from last week", diff < 0)


def sheet_table(week: dict) -> str:
    weights = sorted({p["weight_lb"] for p in week["prices"]})
    rows = []
    for w in weights:
        cells = [f"{w} lb"]
        for cls in ("Steers", "Heifers"):
            p = price_at(week, cls, w)
            cells.append(f'{money(p["price"])}/cwt<br><small>{money(p["low"])} to {money(p["high"])}</small>' if p else "&ndash;")
            cells.append(money(p["price"] * w / 100) if p else "&ndash;")
        rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    return f"""<div class="table-scroll">
      <table class="results sheet">
        <thead><tr><th>Weight</th><th>Steers</th><th>a head</th><th>Heifers</th><th>a head</th></tr></thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
    </div>"""


def history_chart(barn: dict, nice_date) -> str:
    pts = []
    for w in reversed((barn.get("weeks") or [])[:HISTORY_WEEKS]):
        p = price_at(w, "Steers", WEIGHT)
        if p and w["fresh"]:
            d = date.fromisoformat(w["date"])
            pts.append((f"{d:%b} {d.day}", p["price"], p["low"], p["high"]))
    if len(pts) < 2:
        return '<p class="note">The chart fills in week by week: this barn\'s history starts with this week.</p>'
    return charts.barn_history(pts)


def month_list(months: list[int]) -> str:
    names = [charts.MONTH_ABBR[m - 1] for m in months]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def season_words(season: dict, barn_name: str) -> str:
    """One or two plain sentences for a best-months chart."""
    best, worst = charts.MONTH_ABBR[season["best"] - 1], charts.MONTH_ABBR[season["worst"] - 1]
    typical = {m["month"]: m["index"] for m in season["typical"]}
    what = season["label"].split(",")[0].lower()
    if not season["own_months"]:
        return (f"{e(barn_name)} sells {e(what)} mainly in {month_list(season['sells_months'])}: too few months for a "
                f"pattern of its own, so the region's typical year is shown for reference.")
    text = (f"{e(what.capitalize())} here typically bring the most in <strong>{best}</strong> (about "
            f"{(typical[season['best']] - 1) * 100:+.0f}% vs an average month) and the least in "
            f"<strong>{worst}</strong> (about {(typical[season['worst']] - 1) * 100:+.0f}%).")
    if not season["clear"]:
        text += " That gap is within the year-to-year noise, so treat it as a lean, not a rule."
    recent = season.get("this_season") or []
    if recent:
        last = recent[-1]
        m = int(last["month"][5:7])
        usual = typical.get(m)
        now = (last["ratio"] - 1) * 100
        text += (f" This season's latest month, {charts.MONTH_ABBR[m - 1]} {last['month'][:4]}, ran {now:+.0f}%"
                 + (f"; a typical {charts.MONTH_ABBR[m - 1]} runs {(usual - 1) * 100:+.0f}%." if usual else "."))
    return text


def seasons_section(barn: dict) -> str:
    """Best Months to Sell: for each weight class, the typical year and this season (Herd Planner, Milestone 16)."""
    seasons = barn.get("seasons") or []
    if not seasons:
        return ""
    blocks = []
    for season in seasons:
        blocks.append(f"""<h3>{e(season['label'])}</h3>
    <p>{season_words(season, barn['name'])}</p>
    <p class="chart-title">% above or below an average month</p>
    {charts.best_months(season, barn['name'])}
    {charts.best_months_table(season)}""")
    markets = seasons[0].get("markets", 0)
    this_season_note = ("This season: each of the last 12 months compared with this year's own trend line (the "
                        "newest months can't be measured the typical way yet), so it is noisier. "
                        if any(s.get("this_season") for s in seasons) else "")
    return f"""<h2>Best Months to Sell</h2>
    <p class="lede">Calves and heavy feeders run opposite seasons: calves usually bring the least in the fall run
      and the most in spring; heavy feeders the most in late summer. The typical year is measured on
      {markets} markets' USDA reports since 2021, with the market's overall rise taken out; barns don't differ
      beyond the year-to-year noise, so each barn shows the region's pattern for the months it sells.</p>
    {"".join(blocks)}
    <p class="note">{this_season_note}A tendency, not a forecast: a drought or a
      market shock can override it in any year. The best price per pound isn't always the best time to sell: a
      calf you keep also gains weight and eats feed, which <a href="herd-planner.html">Herd Planner</a> weighs
      for each animal.</p>"""


def barn_page(slug: str, barn: dict, all_barns: dict, data: dict, nice_date) -> tuple[str, str, str]:
    """(title, description, body) for one barn's page."""
    where = place(barn)
    state_name = STATE_NAMES.get(barn.get("state"), barn.get("state") or "")
    week = current(barn)
    latest = (barn.get("weeks") or [None])[0]
    title = f"{barn['name']}, {where}: feeder cattle prices this week"
    if week:
        steer, heifer = price_at(week, "Steers", WEIGHT), price_at(week, "Heifers", WEIGHT)
        sold = date.fromisoformat(week["last_sale"])
        desc = (f"{where} feeder cattle prices, week of {nice_date(week['date'])}: 550 lb steers "
                f"{money(steer['price'])}/cwt ({money(steer['low'])} to {money(steer['high'])})"
                + (f", 550 lb heifers {money(heifer['price'])}/cwt" if heifer else "") + ".")
        headline = f"""<div class="barn-now">
        <p class="live-label">550 lb steer, sale of {sold:%b} {sold.day}</p>
        <p class="barn-price">{money(steer['price'])}/cwt{change_flag(barn)}</p>
        {hero.range_bar(steer['low'], steer['price'], steer['high'], steer['low'] * 0.97, steer['high'] * 1.03,
                        (money(steer['low']), '', money(steer['high'])), marker='this sale')}
        <p class="note">About {money(steer['price'] * WEIGHT / 100)} a head. 8 in 10 sales like it land between
          {money(steer['low'])} and {money(steer['high'])}/cwt.</p>
      </div>"""
        sheet = f"<h2>This Week's Price Sheet</h2>\n    {sheet_table(week)}"
    else:
        last = f" Its last sale in our data was {nice_date(latest['last_sale'])}." if latest else ""
        desc = f"{where} feeder cattle prices from {barn['name']}, worked out from USDA auction reports each week."
        headline = f"""<div class="barn-now quiet"><p class="barn-price">No sale in the last three weeks</p>
        <p class="note">{e(barn['name'])} hasn't reported a sale to USDA in three weeks, so there's no price for
          this week.{e(last)}</p></div>"""
        sheet = ""
    others = sorted(((s, b) for s, b in all_barns.items() if s != slug and b.get("state") == barn.get("state")),
                    key=lambda sb: sb[1].get("city") or sb[1]["name"])
    other_list = "".join(f'<li><a href="{page_name(s, b)}">{e(b["name"])}</a>, {e(place(b))}</li>' for s, b in others)
    others_html = (f'<h2>Other Barns in {e(state_name)}</h2>\n    <ul class="plain barn-list">{other_list}</ul>'
                   if other_list else "")
    hub_note = (" This barn is the hub: its prices come straight from the model fitted on its own sales."
                if barn.get("is_hub") else "")
    body = f"""<section class="page barn-page">
  <div class="wrap">
    <p class="eyebrow"><a href="barns.html">Barn Prices</a> &rsaquo; {e(state_name)}</p>
    <h1>{e(barn['name'])}</h1>
    <p class="lede">{e(where)}{" &middot; " + e(barn['sale']) if barn.get('sale') else ""}. Feeder cattle prices,
      worked out every Friday from USDA auction reports.</p>
    <div class="barn-grid">
      {headline}
      <div class="barn-cta card">
        <h2>Price Your Own Cattle Here</h2>
        <p>Herd Planner prices every animal in your herd at this barn, by weight and grade, and tells you
          which to sell and which to keep.</p>
        <p><a class="btn" href="herd-planner.html">About Herd Planner</a></p>
      </div>
    </div>
    {sheet}
    <h2>The Last {HISTORY_WEEKS} Weeks</h2>
    <p class="chart-title">550 lb steer, $/cwt: the dot is the price, the bar the range 8 in 10 sales fell in</p>
    {history_chart(barn, nice_date)}
    {seasons_section(barn)}
    {others_html}
    <h2>Where the Numbers Come From</h2>
    <p>{e(data.get('method', ''))}{hub_note} Medium and large frame, muscle grade 1 cattle.</p>
    <p class="meta">Source: {e(data.get('source', 'USDA AMS auction reports'))}. Estimates, not quotes:
      check with the barn before you sell. <a href="methods.html#herd-planner">How we test Herd Planner</a>.</p>
  </div>
</section>"""
    return title, desc, body


def index_page(all_barns: dict, nice_date) -> str:
    by_state: dict[str, list] = {}
    for slug, barn in all_barns.items():
        by_state.setdefault(barn.get("state") or "Other", []).append((slug, barn))
    sections = []
    for state in sorted(by_state, key=lambda s: STATE_NAMES.get(s, s)):
        rows = []
        for slug, barn in sorted(by_state[state], key=lambda sb: sb[1].get("city") or sb[1]["name"]):
            week = current(barn)
            p = price_at(week, "Steers", WEIGHT) if week else None
            price = f"{money(p['price'])}/cwt" if p else '<span class="note">no recent sale</span>'
            latest = (barn.get("weeks") or [None])[0]
            sold = nice_date(latest["last_sale"]) if latest else "&ndash;"
            town = f'<span class="barn-town">{e(barn["city"])}</span>' if barn.get("city") else ""
            rows.append(f'<tr><td><a href="{page_name(slug, barn)}">{e(barn["name"])}</a>{town}</td>'
                        f'<td>{sold}</td><td>{price}</td></tr>')
        sections.append(f"""    <h2>{e(STATE_NAMES.get(state, state))}</h2>
    <div class="table-scroll"><table class="results barns-table">
      <thead><tr><th>Sale barn</th><th>Last sale</th><th>550 lb steer</th></tr></thead>
      <tbody>{"".join(rows)}</tbody></table></div>""")
    body = "\n".join(sections) if sections else '    <p class="note">The first prices arrive with Friday\'s update.</p>'
    return f"""<section class="page">
  <div class="wrap">
    <h1>Sale Barn Prices</h1>
    <p class="lede">What feeder cattle are bringing at each sale barn Herd Planner follows, worked out every Friday
      from USDA auction reports, with the range real sales fall in.</p>
{body}
  </div>
</section>"""
