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

import json
import math
import re
import urllib.parse
from datetime import date
from html import escape
from pathlib import Path

import charts
import config
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


def steer_change(barn: dict) -> int | None:
    """The 550 lb steer price against last week's at this same barn, in whole dollars per cwt; None when either week
    is missing or stale."""
    weeks = barn.get("weeks") or []
    if len(weeks) < 2 or not weeks[0]["fresh"] or not weeks[1]["fresh"]:
        return None
    now, before = price_at(weeks[0], "Steers", WEIGHT), price_at(weeks[1], "Steers", WEIGHT)
    if not now or not before:
        return None
    return round(now["price"]) - round(before["price"])


def steer_now(barn: dict) -> dict | None:
    """This week's 550 lb steer for My Farm's From Your Barns cards (2026-10-23; Scott chose
    farm-account/notes/from-barns-cards-*-2026-10-23.png): the same numbers the barn's page shows. None when the barn
    hasn't sold in three weeks. hub: the price is from this barn's own sale; otherwise it is the week's estimate."""
    week = current(barn)
    steer = week and price_at(week, "Steers", WEIGHT)
    if not steer:
        return None
    return {"price": round(steer["price"], 2), "low": round(steer["low"], 2), "high": round(steer["high"], 2),
            "week": week["date"], "sale": week["last_sale"], "hub": bool(barn.get("is_hub")),
            "change": steer_change(barn)}


def change_flag(barn: dict) -> str:
    """The 550 lb steer price against last week's, at this same barn."""
    diff = steer_change(barn)
    if diff is None:
        return ""
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


CONTACTS = Path(__file__).resolve().parent / "content" / "barn_contacts.json"
# 2026-10-24 (Scott chose "Both" and A, company-site/notes/barn-from-the-air-*-2026-10-24.png): where each barn's pin
# goes, from its premises address on USDA APHIS's list of approved markets (or checked on the photo by Scott)
SPOTS = Path(__file__).resolve().parent / "content" / "barn_spots.json"
PHOTO = "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/export"
PHOTO_W, PHOTO_H, PHOTO_M = 1280, 720, 900.0   # pixels, and the ground metres across the still photo


def load_contacts(path: Path = CONTACTS) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("barns", {})
    except FileNotFoundError:
        return {}


def contact_section(slug: str, barn: dict, contacts: dict) -> str:
    """Contact the Barn (Scott, 2026-10-12): the barn's business details where we've checked them
    (content/barn_contacts.json, each with its source and date), and on every page a map of the barn's town and
    USDA's own page for the sale. Sale days and times change, so it says to call before hauling, and that we
    aren't the barn. 2026-10-20, Scott: the link belongs "up top after the text ... Just a simple" link: the lede
    ends with Contact the Barn, which jumps here (worded for the barn, since this page is ours, not the barn's)."""
    c = contacts.get(slug) or {}
    lines = []
    if c.get("address"):
        lines.append(f"<li><b>Address:</b> {e(c['address'])}</li>")
    if c.get("phone"):
        tel = re.sub(r"[^0-9+]", "", c["phone"])
        lines.append(f'<li><b>Phone:</b> <a href="tel:{e(tel)}">{e(c["phone"])}</a></li>')
    if c.get("website"):
        lines.append(f'<li><b>Website:</b> <a href="{e(c["website"])}" rel="noopener">{e(c["website"].split("//")[-1].rstrip("/"))}</a></li>')
    query = urllib.parse.quote(f'{barn["name"]}, {c.get("address") or place(barn)}')
    links = [f'<a href="https://www.google.com/maps/search/?api=1&amp;query={query}" rel="noopener">Map and directions</a>',
             f'<a href="https://mymarketnews.ams.usda.gov/viewReport/{e(slug)}" rel="noopener">USDA&rsquo;s report for this sale</a>']
    source = (f' Details from <a href="{e(c["source_url"])}" rel="noopener">{e(c["source"])}</a>, checked '
              f'{e(short_date(c["checked"]))}.' if c.get("source") else "")
    return f"""<h2 id="contact">Contact the Barn</h2>
    {('<ul class="plain barn-contact">' + "".join(lines) + "</ul>") if lines else ""}
    <p class="barn-links">{" &middot; ".join(links)}</p>
    <p class="note">We aren't connected with {e(barn['name'])}. Sale days and times change: call the barn before you
      haul.{source}</p>
    {two_ways(slug)}"""


# 2026-10-21 (Scott: "something like [Grazing Planner's plans card] but for the Barns. Why to sign up", then "Looks good";
# farm-account/notes/barn-two-ways-*-2026-10-21.png): in place of the "Run this barn?" line. Every row must stay true:
# the free column is what any barn gets today, the other what a barn account adds (claude/subscription-benefits.md).
TWO_WAYS_ROWS = (
    ("Your prices from USDA reports: this week, the last 12 weeks, Best Months", True, "Always the same on both. Never for sale."),
    ("Contact the Barn: your office phone, address and website", True, ""),
    ("People can follow your barn", True, ""),
    ("A notice at the top of your page (we call your office each time)", True, ""),
    ("Post notices yourself, any time, no call", False, ""),
    ("Your sale calendar: sale days, special sales, closings", False, ""),
    ("Sale reminders emailed to people who follow you", False, ""),
    ("Your logo on your page and on the Barn Prices list", False, ""),
    ("Your page&rsquo;s numbers: views and followers each week", False, "Counts only. We never tell you who."),
    ("Your people: Owner, Managers and Staff, each with their own sign-in", False, ""),
)


def load_spots(path: Path = SPOTS) -> dict:
    """{report id: {lat, lon, from, address, checked}}; a spot outside the lower 48 is left out."""
    if not path.exists():
        return {}
    spots = json.loads(path.read_text(encoding="utf-8")).get("barns", {})
    return {k: v for k, v in spots.items() if 24 <= v.get("lat", 0) <= 50 and -125 <= v.get("lon", 0) <= -66}


def photo_url(lat: float, lon: float) -> str:
    """USGS's aerial photo (NAIP, public domain) of a box PHOTO_M across centred on the spot, as one still image."""
    x = lon * 20037508.342789244 / 180
    y = math.log(math.tan((90 + lat) * math.pi / 360)) * 20037508.342789244 / math.pi
    half_w = PHOTO_M / 2 / math.cos(math.radians(lat))     # ground metres to Web Mercator metres
    half_h = half_w * PHOTO_H / PHOTO_W
    bbox = f"{x - half_w:.0f},{y - half_h:.0f},{x + half_w:.0f},{y + half_h:.0f}"
    return f"{PHOTO}?bbox={bbox}&bboxSR=3857&imageSR=3857&size={PHOTO_W},{PHOTO_H}&format=jpg&f=image"


def air_section(slug: str, barn: dict, spots: dict) -> str:
    """See the Barn from the Air: the still photo with the pin, and Fly Over the Barn, which loads the 3D map
    (barn-air.js; nothing loads from MapLibre until it's pressed). No section for a barn without a spot."""
    spot = spots.get(slug)
    if not spot:
        return ""
    name = e(barn["name"])
    where = ("The pin was placed on the barn on the aerial photo." if spot.get("from") == "checked" else
             "The pin is at the barn's street address, from USDA's list of approved livestock markets, so it may "
             "sit on the road in front.")
    key = config.google_embed_key()      # 2026-10-25: Street View in the box when there's a key (config.py)
    sv = f' data-sv-key="{e(key)}"' if key else ""
    sv_words = " Street View: Google." if key else ""
    return f"""<div class="barn-air card" id="barn-air" data-lat="{spot['lat']}" data-lon="{spot['lon']}" data-name="{name}"{sv}>
      <h2 id="from-the-air">See the Barn from the Air</h2>
      <div class="air-map" id="air-map">
        <img class="air-photo" src="{e(photo_url(spot['lat'], spot['lon']))}" alt="Aerial photo around {name}" width="{PHOTO_W}" height="{PHOTO_H}" loading="lazy">
        <div class="air-pin" aria-hidden="true"><span>{name}</span><svg width="26" height="34" viewBox="0 0 26 34"><path d="M13 33C13 33 2 20 2 12.5a11 11 0 0 1 22 0C24 20 13 33 13 33z" fill="#e0ac45" stroke="#243b2f" stroke-width="2"/><circle cx="13" cy="12.5" r="4" fill="#243b2f"/></svg></div>
        <button type="button" class="btn air-go" id="air-go">Fly Over the Barn</button>
      </div>
      <p class="note">{where} Imagery: USDA NAIP via USGS The National Map &middot; Terrain: AWS Terrain Tiles &middot;
        Roads: USGS The National Map.{sv_words}</p>
      <script src="barn-air.js" defer></script>
    </div>"""


def two_ways(slug: str) -> str:
    ok = '<span class="tw-ok" role="img" aria-label="Yes">&#10003;</span>'
    no = '<span class="tw-no" role="img" aria-label="No">&ndash;</span>'
    rows = "".join(f'<tr><th scope="row">{words}' + (f'<span class="tw-sub">{sub}</span>' if sub else "") +
                   f'</th><td>{ok if free else no}</td><td class="tw-paid">{ok}</td></tr>' for words, free, sub in TWO_WAYS_ROWS)
    form = f"{e(config.ACCOUNT_ORIGIN)}/barn-update.html?barn={e(slug)}"
    title = ('<p class="tw-title">Two Ways to Run Your Barn&rsquo;s Page</p>'
             '<p class="tw-lede">Your page is free and stays free. A barn account lets you run it yourself.</p>')
    return f"""<section class="two-ways" aria-label="Two ways to run your barn's page">
      <div class="tw-phone-title">{title}</div>
      <table>
        <thead><tr><th scope="col" class="tw-lead">{title}</th>
          <th scope="col"><span class="tw-eb">Free &middot; No Sign-In</span><span class="tw-col">Your Page as It Is</span></th>
          <th scope="col" class="tw-paid"><span class="tw-pill">Free During the Pilot</span><span class="tw-col">Run Your Own Page</span><span class="tw-colsub">With a barn account</span></th></tr></thead>
        <tbody>{rows}</tbody>
        <tfoot><tr><td class="tw-lead">One call to your listed office to check you work there. After that, you post yourself.</td>
          <td><a class="tw-btn" href="{form}" rel="noopener">Update This Page</a></td>
          <td class="tw-paid"><a class="tw-btn-main" href="{form}&amp;account=1" rel="noopener">Ask for a Barn Account</a></td></tr></tfoot>
      </table>
      <p class="tw-foot">Every barn&rsquo;s prices come from USDA auction reports and are worked out the same way, whether or not
        it has an account; no barn can pay for a better price or a better place in the list. We never sell rancher data or
        share who follows a barn.</p>
    </section>"""


def short_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d:%b} {d.day}"


def hub_sale(all_barns: dict) -> str | None:
    """The hub's (Oklahoma City's) latest sale: every other barn's price is worked out from it."""
    hub = next((b for b in all_barns.values() if b.get("is_hub")), None)
    weeks = (hub or {}).get("weeks") or []
    return weeks[0]["last_sale"] if weeks else None


def barn_page(slug: str, barn: dict, all_barns: dict, data: dict, nice_date) -> tuple[str, str, str]:
    """(title, description, body) for one barn's page.

    Dates (Scott, 2026-10-12, "barn pages and search"): a barn's price is Herd Planner's estimate for the week,
    worked out from the hub's (Oklahoma City's) latest sale plus this barn's own measured difference from it, so
    the page says "estimate for the week of ..." and names both sales: the hub's it was worked out from, and the
    last one here. The hub's own page shows its sale. The title and description carry the week, so a search
    result says how fresh it is."""
    where = place(barn)
    state_name = STATE_NAMES.get(barn.get("state"), barn.get("state") or "")
    week = current(barn)
    latest = (barn.get("weeks") or [None])[0]
    title = f"{barn['name']}, {where}: Feeder Cattle Prices"
    if week:
        steer, heifer = price_at(week, "Steers", WEIGHT), price_at(week, "Heifers", WEIGHT)
        week_of, here = nice_date(week["date"]), short_date(week["last_sale"])
        hub_day = hub_sale(all_barns)
        title += f", Week of {week_of}"
        prices = (f"550 lb steers {money(steer['price'])}/cwt ({money(steer['low'])} to {money(steer['high'])})"
                  + (f", 550 lb heifers {money(heifer['price'])}/cwt" if heifer else ""))
        if barn.get("is_hub"):
            desc = f"{where} feeder cattle prices from the sale of {here}: {prices}."
            label = f"550 lb steer, sale of {here}"
            basis = "Worked out from this sale."
        else:
            desc = f"{where} feeder cattle prices, estimated for the week of {week_of}: {prices}. Last sale here {here}."
            label = f"550 lb steer, estimate for the week of {short_date(week['date'])}"
            basis = (f"Worked out from Oklahoma City's {short_date(hub_day)} sale and this barn's usual difference "
                     f"from it. Last sale here: <strong>{here}</strong>." if hub_day else
                     f"Last sale here: <strong>{here}</strong>.")
        headline = f"""<div class="barn-now">
        <p class="live-label">{label}</p>
        <p class="barn-price">{money(steer['price'])}/cwt{change_flag(barn)}</p>
        {hero.range_bar(steer['low'], steer['price'], steer['high'], steer['low'] * 0.97, steer['high'] * 1.03,
                        (money(steer['low']), '', money(steer['high'])), marker='this sale' if barn.get('is_hub') else 'this week')}
        <p class="note">About {money(steer['price'] * WEIGHT / 100)} a head. 8 in 10 sales like it land between
          {money(steer['low'])} and {money(steer['high'])}/cwt.</p>
        <p class="note barn-basis">{basis}</p>
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
    <!-- 2026-10-21 (claude/barn-plan.md Part 1 step 2; Scott chose A of farm-account/notes/barn-logo-*): the barn's
         logo, left of its name, once it has one approved in My Farm (barn-logo.js asks; hidden until then). -->
    <div class="barn-title"><img class="barn-logo" id="barn-logo" data-barn="{e(slug)}" data-barn-logos="{e(config.ACCOUNT_ORIGIN)}" alt="" width="56" height="56" hidden><h1>{e(barn['name'])}</h1></div>
    <script src="barn-logo.js" defer></script>
    <p class="lede">{e(where)}{" &middot; " + e(barn['sale']) if barn.get('sale') else ""}. Feeder cattle prices,
      worked out every Friday from USDA auction reports. <a class="lede-link" href="#contact">Contact the Barn</a></p>
    <!-- 2026-10-20 (claude/barn-plan.md Part 2; Scott chose A of farm-account/notes/barn-alerts-1-follow-button-*.png):
         Follow This Barn. A plain link to My Farm, which signs you in and asks; signed in, barn-follow.js asks here
         instead, in a small box whose email box starts unticked, and once you follow it says Following. -->
    <div class="barn-follow" id="barn-follow" data-account="{e(config.ACCOUNT_ORIGIN)}" data-barn="{e(slug)}">
      <a class="btn-follow" id="bf-button" href="{e(config.ACCOUNT_ORIGIN)}/#follow/{e(slug)}"><span aria-hidden="true">&#9734;</span> Follow This Barn</a>
      <span class="follow-note" id="bf-note">Get its notices by email: sale times, special sales, closings.</span>
      <div class="follow-panel" id="bf-panel" hidden>
        <h2 class="follow-title">Follow {e(barn['name'])}</h2>
        <label class="follow-check"><input type="checkbox" id="bf-email"> Email me this barn's notices at the address on my account</label>
        <p class="follow-small">Usually a few a month. Every email has a Stop These link. We never give your name or email to the barn.</p>
        <div class="follow-acts"><button type="button" class="btn" id="bf-yes">Follow</button>
          <button type="button" class="btn secondary" id="bf-no">Cancel</button></div>
        <p class="follow-small" id="bf-said" role="status"></p>
      </div>
    </div>
    <script src="barn-follow.js" defer></script>
    <!-- 2026-10-20 (Scott: barns "post a current message"; notes/site-claim-page-desk-2026-10-20.png): the barn's own
         notice, read from My Farm when the page opens (barn-notice.js). Hidden until there is one. -->
    <div class="barn-notice" id="barn-notice" role="note" hidden data-src="{e(config.ACCOUNT_ORIGIN)}/barns/{e(slug)}/notice"></div>
    <script src="barn-notice.js" defer></script>
    <!-- 2026-10-21 (Scott: "B is good", farm-account/notes/barn-cal-2-B-*-2026-10-21.png): the barn's own sale calendar,
         kept by the barn in My Farm and drawn a month at a time (barn-calendar.js). Hidden until the barn has one. -->
    <section class="barn-calendar" id="barn-calendar" aria-labelledby="barn-calendar-title" hidden
      data-src="{e(config.ACCOUNT_ORIGIN)}/barns/{e(slug)}/calendar" data-name="{e(barn['name'])}"></section>
    <script src="barn-calendar.js" defer></script>
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
    <!-- 2026-10-20, Scott: the quick link up top "should just link to the bottom of the page where all the contact
         info lives": Contact the Barn is the page's last section, in its own box -->
    {air_section(slug, barn, load_spots())}
    <div class="barn-contact-box card">{contact_section(slug, barn, load_contacts())}</div>
  </div>
</section>"""
    return title, desc, body


def index_page(all_barns: dict, nice_date, markets_html: str = "") -> str:
    by_state: dict[str, list] = {}
    for slug, barn in all_barns.items():
        by_state.setdefault(barn.get("state") or "Other", []).append((slug, barn))
    sections = []
    week_of = max((b["weeks"][0]["date"] for b in all_barns.values() if b.get("weeks")), default=None)
    price_head = f"550 lb steer, week of {short_date(week_of)}" if week_of else "550 lb steer"
    for state in sorted(by_state, key=lambda s: STATE_NAMES.get(s, s)):
        rows = []
        for slug, barn in sorted(by_state[state], key=lambda sb: sb[1].get("city") or sb[1]["name"]):
            week = current(barn)
            p = price_at(week, "Steers", WEIGHT) if week else None
            price = f"{money(p['price'])}/cwt" if p else '<span class="note">no recent sale</span>'
            latest = (barn.get("weeks") or [None])[0]
            sold = nice_date(latest["last_sale"]) if latest else "&ndash;"
            town = f'<span class="barn-town">{e(barn["city"])}</span>' if barn.get("city") else ""
            rows.append(f'<tr><td><a href="{page_name(slug, barn)}" data-barn="{e(slug)}">{e(barn["name"])}</a>{town}</td>'
                        f'<td>{sold}</td><td>{price}</td></tr>')
        sections.append(f"""    <h2>{e(STATE_NAMES.get(state, state))}</h2>
    <div class="table-scroll"><table class="results barns-table">
      <thead><tr><th>Sale barn</th><th>Last sale</th><th>{price_head}</th></tr></thead>
      <tbody>{"".join(rows)}</tbody></table></div>""")
    body = "\n".join(sections) if sections else '    <p class="note">The first prices arrive with Friday\'s update.</p>'
    return f"""<section class="page">
  <div class="wrap">
    <h1>Sale Barn Prices</h1>
    <p class="lede">What feeder cattle are bringing at each sale barn Herd Planner follows, worked out every Friday
      from USDA auction reports, with the range real sales fall in.</p>
{markets_html}{body}
    <span hidden data-barn-logos="{e(config.ACCOUNT_ORIGIN)}"></span><script src="barn-logo.js" defer></script>
  </div>
</section>"""
