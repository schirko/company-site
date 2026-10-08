"""The home page's live panel: this week's real numbers, drawn like a small dashboard.

Where other sites show a screenshot of their app, ours shows the app's real output for this week's
county, rebuilt every Friday (cards.py picks the county; build.py calls panel()). Four tiles:

  1. 550 lb steer price at the nearest sale barn, with the range 8 in 10 sales fell in
  2. how calves usually price this month against the yearly trend (Herd Planner's seasonal index)
  3. the county's trend corn yield and its 1-in-10 low
  4. the county's workable fall field days, typical and wet, drawn as 61 day squares

Each tile carries a short gold callout saying what stands behind the number. Every callout must
stay literally true of that number: they're claims, not decoration.
"""

from datetime import date
from html import escape

BLUE, BLUE_LIGHT, GREY = "#2a78d6", "#b7d3f6", "#e2e0d9"
# Red means one thing everywhere in the panel: the downside (below the trend, a bad year, days lost
# to rain). Blue and red are the data-viz guide's diverging pair, checked for color blindness; red
# never appears alone, always with a down arrow or words saying what it is.
RED, RED_LIGHT = "#e34948", "#f5bdbc"


def e(x) -> str:
    return escape(str(x), quote=True)


# --- tiny charts (inline SVG) --------------------------------------------------------------------


def range_bar(low: float, value: float, high: float | None, lo: float, hi: float,
              labels: tuple[str, str, str], downside: bool = False, marker: str = "") -> str:
    """A band and marker: a pale square band from low to high (or low to value) and a thin dark
    line at the value, with `marker` (e.g. "this sale") written above it.
    Deliberately no track, round ends or knob: those made the old version look like a slider
    people wanted to drag. downside=True paints the band red: the stretch below the value a bad
    year can fall to."""
    w, h = 260, 56
    x = lambda v: 8 + (v - lo) / (hi - lo) * (w - 16)
    right = high if high is not None else value
    parts = [
        f'<rect x="{x(low):.1f}" y="20" width="{x(right) - x(low):.1f}" height="12" rx="2" '
        f'fill="{RED_LIGHT if downside else BLUE_LIGHT}"/>',
        f'<line x1="{x(value):.1f}" x2="{x(value):.1f}" y1="15" y2="37" class="marker"/>',
        f'<text x="{x(low):.1f}" y="52" text-anchor="middle" class="tick">{e(labels[0])}</text>',
    ]
    if marker:
        parts.append(f'<text x="{x(value):.1f}" y="10" text-anchor="middle" class="tick">{e(marker)}</text>')
    if high is not None:
        parts.append(f'<text x="{x(high):.1f}" y="52" text-anchor="middle" class="tick">{e(labels[2])}</text>')
    else:
        parts.append(f'<text x="{x(value):.1f}" y="52" text-anchor="middle" class="tick">{e(labels[1])}</text>')
    return f'<svg class="mini" viewBox="0 0 {w} {h}" aria-hidden="true">{"".join(parts)}</svg>'


def month_strip(index: list[float], current: int) -> str:
    """Twelve small bars around zero (% vs trend): blue above the trend, red below; this month in
    full color, the other months pale."""
    w, h, mid = 260, 70, 32
    band = (w - 8) / 12
    parts = [f'<line x1="4" x2="{w - 4}" y1="{mid}" y2="{mid}" stroke="#b9b6ad" stroke-width="1"/>']
    for m, v in enumerate(index):
        pct = (v - 1) * 100
        bh = abs(pct) * 4  # 4 px per percentage point: +/-6% fits
        x = 4 + band * m + band * 0.2
        bw = band * 0.6
        y = mid - bh if pct > 0 else mid
        if pct >= 0:
            color = BLUE if m == current else BLUE_LIGHT
        else:
            color = RED if m == current else RED_LIGHT
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{max(bh, 1):.1f}" rx="2" fill="{color}"/>')
        parts.append(f'<text x="{x + bw / 2:.1f}" y="{h - 4}" text-anchor="middle" class="tick{" now" if m == current else ""}">'
                     f'{"JFMAMJJASOND"[m]}</text>')
    return f'<svg class="mini" viewBox="0 0 {w} {h}" aria-hidden="true">{"".join(parts)}</svg>'


def day_squares(typical: float, wet: float, total: int = 61) -> str:
    """61 squares, one per day Oct 1 - Nov 30: dark blue = workable even in a wet fall, light blue =
    the extra workable days a typical fall adds, red = too wet to work even in a typical fall.
    Drawn as one path per color (a short "move, square" command per day) rather than 61 separate
    shapes, which keeps the county picker's data file small; the round stroke softens the corners."""
    cols, size, gap = 21, 9, 3.4
    rows = -(-total // cols)
    w, h = cols * (size + gap), rows * (size + gap)
    runs = {BLUE: [], BLUE_LIGHT: [], RED_LIGHT: []}
    for d in range(total):
        c = BLUE if d < round(wet) else BLUE_LIGHT if d < round(typical) else RED_LIGHT
        x, y = 0.7 + (d % cols) * (size + gap), 0.7 + (d // cols) * (size + gap)
        runs[c].append(f"M{x:.1f} {y:.1f}h{size}v{size}h-{size}z")
    paths = "".join(f'<path d="{"".join(cmds)}" fill="{c}" stroke="{c}" stroke-width="1.4" stroke-linejoin="round"/>'
                    for c, cmds in runs.items() if cmds)
    return f'<svg class="mini days" viewBox="0 0 {w:.0f} {h:.0f}" aria-hidden="true">{paths}</svg>'


# --- the panel -----------------------------------------------------------------------------------


def badge(text: str, down: bool) -> str:
    """A small up or down flag beside the headline: arrow + words, so color is never the only cue."""
    arrow = "\u25bc" if down else "\u25b2"
    return f'<span class="badge {"down" if down else "up"}"><span aria-hidden="true">{arrow}</span> {e(text)}</span>'


def tile(href: str, callout: str, label: str, headline: str, chart: str, note: str, extra_class: str = "",
         flag: str = "", slot: str = "") -> str:
    """One stat tile. `slot` names it (herd, calves, corn, days) so the county picker can swap it."""
    return f"""        <a class="live-tile{extra_class}" href="{e(href)}" data-tile="{e(slot)}">
          <span class="callout">{e(callout)}</span>
          <span class="live-label">{e(label)}</span>
          <span class="live-headline">{e(headline)}{flag}</span>
          {chart}
          <span class="live-note">{e(note)}</span>
        </a>"""


def money(x: float) -> str:
    return f"${x:,.0f}"


# --- the four tiles, one function each (the county picker reuses them) ---------------------------


STEER = "550 lb steer"


def steer_label(card: dict | None) -> str:
    """The steer price's label with the day of the sale it comes from: "550 lb steer, sale of Sep 16".
    It used to say "this week", but the price is the nearest barn's latest sale in the last three weeks, so it
    can be two weeks old; Scott asked for a real date here, as the field-days tile has (October 7, 2026).
    With no fresh price there is no sale to name, and the label says "this week"."""
    if not card or not card.get("as_of"):
        return f"{STEER}, this week"
    sold = date.fromisoformat(card["as_of"])
    return f"{STEER}, sale of {sold:%b} {sold.day}"


def herd_tile(herd: dict | None, state_name: str, barn_href=None) -> str:
    """barn_href(slug) gives that barn's page on the site, or None; the tile then links there."""
    if not herd:
        return tile("herd-planner.html", "USDA auction reports", steer_label(None), "No fresh price", "",
                    (f"No sale barn near {state_name} reported in the last three weeks. " if state_name else
                     "No sale barn nearby reported in the last three weeks. ") + "Prices update every Friday.",
                    " quiet", slot="herd")
    href = (barn_href(herd.get("market_slug")) if barn_href and herd.get("market_slug") else None) or "herd-planner.html"
    return tile(
        href, "8 in 10 sales land in this range", steer_label(herd),
        f'{money(herd["value"])}/cwt',
        range_bar(herd["low"], herd["value"], herd["high"], herd["low"] * 0.97, herd["high"] * 1.03,
                  (money(herd["low"]), "", money(herd["high"])), marker="this sale"),
        f'About {money(herd["value"] * 5.5)} a head at {herd["market"]}.', slot="herd")   # the sale's day is in the label


# --- the steer tile by barn (October 2026) ---------------------------------------------------------
# Scott: a rancher whose barn has no fresh price is told so and offered the nearest barns that have one
# (option A of the 2026-10-07 mockups), never handed another barn's price as if it were his. cards.choose
# picks which tile a county gets; panel.js makes the same choice in the browser, from pieces drawn here.
# The tile is a box with its main link stretched over it, because the nearby barns are links of their own
# and a link can't sit inside a link.

CHANGE = '<a class="live-change" href="#live-pick" data-change-barn hidden>Change barn</a>'
NEAR = "<!--near-->"  # where a quiet tile's nearby barns go; panel.js fills it the same way
NEAR_HEAD = {"near": "Fresh nearby, $/cwt", "benchmark": "Nothing fresh nearby. The national benchmark, $/cwt:"}


def day(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d:%b} {d.day}"


def barn_card(b: dict) -> dict:
    """A barn's latest steer price (cards.barns_now) in the shape herd_tile and herd_pin take."""
    return {"value": b["value"], "low": b["low"], "high": b["high"], "as_of": b["last_sale"],
            "market": f'{b["name"]}, {b["city"]} {b["state"]}', "market_slug": int(b["slug"])}


def box_tile(href: str, callout: str, label: str, headline: str, chart: str, note_html: str, extra_class: str = "") -> str:
    return f"""        <div class="live-tile{extra_class}" data-tile="herd">
          <span class="callout">{e(callout)}</span>
          <span class="live-label">{e(label)}</span>
          <a class="live-main" href="{e(href)}"><span class="live-headline">{e(headline)}</span></a>
          {chart}
          <span class="live-note">{note_html}</span>
        </div>"""


def barn_page(b: dict, barn_href=None) -> str:
    return (barn_href(b["slug"]) if barn_href else None) or "herd-planner.html"


def barn_tile(b: dict, barn_href=None, benchmark: bool = False) -> str:
    """The barn's fresh price, as herd_tile draws it, naming the town; the benchmark says why it's shown."""
    card, town = barn_card(b), f'{b["city"]}, {b["state"]}'
    head = money(b["value"] * 5.5)
    note = (f"About {head} a head at {town}, the national benchmark: no barn within 250 miles has sold in "
            f"three weeks." if benchmark else f"About {head} a head at {town}.")
    return box_tile(barn_page(b, barn_href), "8 in 10 sales land in this range", steer_label(card),
                    f'{money(b["value"])}/cwt',
                    range_bar(b["low"], b["value"], b["high"], b["low"] * 0.97, b["high"] * 1.03,
                              (money(b["low"]), "", money(b["high"])), marker="this sale"),
                    f"{e(note)} {CHANGE}")


def near_row(b: dict, barn_href=None) -> str:
    """One nearby barn: its town, its price and the day it sold, linking to its page."""
    return (f'<a href="{e(barn_page(b, barn_href))}"><span class="near-name">{e(b["city"])}</span>'
            f'<span class="near-fig"><b>{e(money(b["value"]))}</b><small> &middot; {e(day(b["last_sale"]))}</small></span></a>')


def near_block(kind: str, rows: list[str]) -> str:
    return f'<span class="near"><span class="near-head">{e(NEAR_HEAD[kind])}</span>{"".join(rows)}</span>' if rows else ""


def quiet_tile(b: dict, barn_href=None, near: str = NEAR) -> str:
    """A chosen barn with no sale in three weeks: said plainly, then `near` (the nearby barns, or NEAR for
    panel.js to fill)."""
    return box_tile(barn_page(b, barn_href), "USDA auction reports", f'{STEER} at {b["city"]}', "No fresh price",
                    near, f'{e(b["city"])} last sold {e(day(b["last_sale"]))}. {CHANGE}', " quiet")


def barn_pin(b: dict, barn_href=None, benchmark: bool = False) -> str:
    if benchmark:
        return pin("herd", barn_page(b, barn_href), steer_label(barn_card(b)), f'{e(money(b["value"]))}<small>/cwt</small>',
                   f'{b["city"]} {b["state"]} \u00b7 the national benchmark')
    return herd_pin(barn_card(b), "", barn_href)


def quiet_pin(b: dict, barn_href=None) -> str:
    return pin("herd", barn_page(b, barn_href), f'{STEER} at {b["city"]}', "No fresh price",
               f'Last sale {day(b["last_sale"])}', quiet=True)


def steer_for(choice: dict, barns: dict, barn_href=None) -> tuple[str, str]:
    """(tile, pin) for cards.choose's answer."""
    kind = choice["kind"]
    if kind == "none":
        return herd_tile(None, "", barn_href), herd_pin(None, "", barn_href)
    b = barns[choice["barn"]]
    if kind == "benchmark":
        return barn_tile(b, barn_href, benchmark=True), barn_pin(b, barn_href, benchmark=True)
    if kind == "barn":
        return barn_tile(b, barn_href), barn_pin(b, barn_href)
    rows = [near_row(barns[s], barn_href) for s in choice["rows"]]
    if choice.get("benchmark"):
        near = near_block("benchmark", [near_row(barns[choice["benchmark"]], barn_href)])
    else:
        near = near_block("near", rows)
    return quiet_tile(b, barn_href, near), quiet_pin(b, barn_href)


def calves_tile(season: dict, when: date) -> str:
    m = when.month - 1
    calves = season["series"][0]["index"]
    pct = (calves[m] - 1) * 100
    return tile(
        "herd-planner.html#calf-season", "Oklahoma City sales, 2021-2026", f'Calves in {season["months"][m]}, vs the yearly trend',
        f"{pct:+.0f}%".replace("-", "−"), month_strip(calves, m),
        "Lowest in October and November, highest in March. Tendencies, not guarantees.",
        flag=badge("below trend" if pct < 0 else "above trend", pct < 0), slot="calves")


def corn_tile(corn: dict | None, where: str, not_covered: str = "") -> str:
    if not corn:
        return tile("corn-yield-predictor.html", "USDA county yields since 2000", "Trend corn yield", "Not covered yet", "",
                    f"No corn numbers for {where} yet. {not_covered}", " quiet", slot="corn")
    return tile(
        "corn-yield-predictor.html", "USDA county yields since 2000", corn["label"], corn["headline"],
        range_bar(corn["low"], corn["value"], None, corn["low"] * 0.94, corn["value"] * 1.04,
                  (f'{corn["low"]:.0f} low', f'{corn["value"]:.0f} trend', ""), downside=True),
        f'Trend for {where}. Red: how far a bad year (1 in 10) falls, to below {corn["low"]:.0f} bu/acre.',
        flag=badge(f'{round(corn["value"]) - round(corn["low"])} bu in a bad year', True), slot="corn")


def days_tile(days: dict | None, where: str, not_covered: str = "") -> str:
    if not days:
        return tile("farm-equipment-planner.html", "Real falls on record, day by day", "Fall field days, Oct 1 to Nov 30",
                    "Not covered yet", "", f"No weather yet for {where}. {not_covered}", " quiet", slot="days")
    return tile(
        "farm-equipment-planner.html", "Real falls on record, day by day", days["label"], days["headline"],
        day_squares(days["value"], days["low"]),
        f'Dark blue: workable even in a wet fall ({round(days["low"])}). Light blue: extra days in a typical fall. '
        f'Red: too wet to work.',
        flag=badge(f'{61 - round(days["low"])} lost in a wet fall', True), slot="days")  # rounded once, so words, squares and badge agree


# --- the pins: three of this week's numbers set on the home page's photo --------------------------
#
# The top of the home page is a photo of cattle on open range with three live figures pinned on it
# (option C of the 2026-10-03 mockups: "numbers on the land"). The photo says agriculture and
# livestock; the pins say metrics, and they are the same real numbers as the panel below, drawn from
# the same cards. Each pin is named by its slot (herd, land, corn) so the county picker can swap it.


def pin(slot: str, href: str, label: str, figure: str, note: str, quiet: bool = False) -> str:
    """`figure` is HTML (a number with a small unit, or an arrow and words); everything else is text."""
    return (f'        <a class="pin{" quiet" if quiet else ""}" href="{e(href)}" data-pin="{e(slot)}">'
            f'<span class="pin-label">{e(label)}</span><span class="pin-fig">{figure}</span>'
            f'<span class="pin-note">{e(note)}</span></a>')


def herd_pin(herd: dict | None, state_name: str, barn_href=None) -> str:
    if not herd:
        return pin("herd", "herd-planner.html", steer_label(None), "No fresh price",
                   f"No sale barn near {state_name} reported in three weeks" if state_name else
                   "No sale barn nearby reported in three weeks", quiet=True)
    href = (barn_href(herd.get("market_slug")) if barn_href and herd.get("market_slug") else None) or "herd-planner.html"
    barn = herd["market"].rsplit(",", 1)[-1].strip()  # "Bassett Livestock Auction, Bassett NE" -> "Bassett NE"
    return pin("herd", href, steer_label(herd), f'{e(money(herd["value"]))}<small>/cwt</small>',
               f'{barn} \u00b7 8 in 10 sales {money(herd["low"])} to {money(herd["high"])}')


def grass_pin(grass: dict, county: str) -> str:
    """Grass against normal, from the Grazing Planner (Nebraska weeks only). Red is the downside and never
    comes alone: an arrow and the words "below normal" go with it."""
    pct = round(abs(grass["value"]) * 100)
    if pct <= 2:
        figure = "About normal"
    elif grass["value"] < 0:
        figure = f'<span class="down" aria-hidden="true">\u25bc</span> {pct}%<small> below normal</small>'
    else:
        figure = f'<span aria-hidden="true">\u25b2</span> {pct}%<small> above normal</small>'
    return pin("land", "grazing-planner.html", "Grass this season", figure, f'{county}, {grass.get("season", "")}'.rstrip(", "))


def days_pin(days: dict | None, county: str) -> str:
    if not days:
        return pin("land", "farm-equipment-planner.html", "Fall field days, Oct 1 to Nov 30", "Not covered yet",
                   f"No weather yet for {county}", quiet=True)
    return pin("land", "farm-equipment-planner.html", "Fall field days, Oct 1 to Nov 30",
               f'{round(days["value"])}<small> of 61 days</small>', f'{round(days["low"])} in a wet fall (1 in 10)')


def corn_pin(corn: dict | None, county: str) -> str:
    if not corn:
        return pin("corn", "corn-yield-predictor.html", "Trend corn yield", "Not covered yet",
                   f"No corn numbers for {county} yet", quiet=True)
    return pin("corn", "corn-yield-predictor.html", corn["label"], f'{corn["value"]:.0f}<small> bu/acre</small>',
               f'{corn["low"]:.0f} in a bad year (1 in 10)')


def land_pin(cards: dict, county: str) -> str:
    """The middle pin: this season's grass when the Grazing Planner covers the week's county, otherwise fall
    field days (which every county the Equipment Planner covers has)."""
    grass = cards.get("grazing-planner")
    return grass_pin(grass, county) if grass else days_pin(cards.get("farm-equipment-planner"), county)


def pins(week: dict, barn_href=None, steer_pin: str | None = None) -> str:
    """steer_pin: the herd pin for the barn cards.choose picked (build.py); without it, the week's saved card."""
    place, cards = week["place"], week["cards"]
    where = f'{place["county"]}, {place["state_name"]}'
    rows = [steer_pin or herd_pin(cards.get("herd-planner"), place["state_name"], barn_href),
            land_pin(cards, place["county"]),
            corn_pin(cards.get("corn-yield-predictor"), place["county"])]
    return f"""      <div class="pins" id="pins" role="group" aria-label="This week's numbers">
{chr(10).join(rows)}
        <p class="pins-foot"><span class="live-dot" aria-hidden="true"></span> Real numbers this week: <span class="pins-where">{e(where)}</span></p>
      </div>"""


PICKER = """      <form class="live-pick" id="live-pick" hidden>
        <label>State <select name="state"></select></label>
        <label>County <select name="county"></select></label>
        <label>Sale barn <select name="barn"></select></label>
        <button type="submit" class="btn small">Show</button>
        <button type="button" class="linklike live-pick-reset">County of the week</button>
      </form>"""


def panel(week: dict, stories: list[dict], nice_date, barn_href=None, steer_tile: str | None = None) -> str:
    place = week["place"]
    where = f'{place["county"]}, {place["state_name"]}'
    cards = week["cards"]
    season = next((s for s in stories if s["chart"] == "seasonal"), None)
    tiles = [steer_tile or herd_tile(cards.get("herd-planner"), place["state_name"], barn_href)]
    if season:
        tiles.append(calves_tile(season, date.fromisoformat(week["date"])))
    tiles.append(corn_tile(cards.get("corn-yield-predictor"), where))
    tiles.append(days_tile(cards.get("farm-equipment-planner"), where))
    # The picker's button and form start hidden: panel.js shows them, so a browser without
    # JavaScript sees the county of the week and nothing that doesn't work.
    return f"""    <div class="live" id="this-week" data-week-place="{e(where)}">
      <div class="live-top">
        <p class="live-head"><span class="live-dot" aria-hidden="true"></span> New every Friday &middot; week of {nice_date(week["date"])}</p>
      </div>
      <div class="live-name">
        <h2><span class="live-title">This Week</span>: <span class="live-where">{e(where)}</span></h2>
        <button type="button" class="live-pick-open" hidden aria-expanded="false" aria-controls="live-pick">See your county</button>
      </div>
{PICKER}
      <div class="live-grid" aria-live="polite">
{chr(10).join(tiles)}
      </div>
      <p class="live-foot">One farm county each week, real numbers from each app.
        <a href="methods.html">How we test them</a></p>
    </div>
    <script src="panel.js" defer></script>"""


def panel_data(week: dict, counties: list[dict], static_cards: dict, not_covered: dict, state_names: dict,
               barn_href=None, barns: dict | None = None, near_of=None, hub: str | None = None,
               fresh_days: int = 21) -> dict:
    """Everything the county picker needs, each tile already drawn by the same functions as the page,
    so a picked county looks exactly like the county of the week. build.py writes it to
    docs/panel-data.json; panel.js reads it only when a visitor asks for their county."""
    by_state = week.get("herd_by_state") or {}
    out = {"format": 3, "week": week["week"], "default": week["place"]["fips"],
           "states": {code: state_names[code] for code in sorted({c["state"] for c in counties})},
           "herd": {code: herd_tile(by_state.get(code), state_names[code], barn_href) for code in state_names},
           # The pins on the photo follow the picked county too (format 2). Grass is only known for the county of
           # the week, so a picked county's middle pin is its fall field days.
           "herd_pin": {code: herd_pin(by_state.get(code), state_names[code], barn_href).strip() for code in state_names},
           "counties": {}}
    # Format 3 (October 2026): the steer tile by barn. Every barn's pieces, drawn here; each county's barns
    # within 250 miles, nearest first; panel.js picks among them with the visitor's own date (a price ages
    # out of "fresh" during the week) and their chosen barn. Without barn positions it uses "herd" above.
    if barns and near_of:
        out["barns"] = {}
        for slug, b in barns.items():
            pieces = {"city": b["city"], "state": b["state"], "last_sale": b["last_sale"],
                      "tile": barn_tile(b, barn_href).strip(), "quiet": quiet_tile(b, barn_href).strip(),
                      "row": near_row(b, barn_href), "pin": barn_pin(b, barn_href).strip(),
                      "quiet_pin": quiet_pin(b, barn_href).strip()}
            if slug == hub:
                pieces["bench_tile"] = barn_tile(b, barn_href, benchmark=True).strip()
                pieces["bench_pin"] = barn_pin(b, barn_href, benchmark=True).strip()
            out["barns"][slug] = pieces
        out.update({"hub": hub, "fresh_days": fresh_days, "near_head": NEAR_HEAD, "near_token": NEAR,
                    "none_tile": herd_tile(None, "", barn_href).strip(), "none_pin": herd_pin(None, "", barn_href).strip()})
    for c in counties:
        where = f'{c["name"]}, {state_names[c["state"]]}'
        out["counties"][c["fips"]] = {
            "name": c["name"], "state": c["state"],
            "corn": corn_tile(static_cards["corn"].get(c["fips"]), where, not_covered["corn"]),
            "days": days_tile(static_cards["days"].get(c["fips"]), where, not_covered["days"]),
            "pins": {"land": days_pin(static_cards["days"].get(c["fips"]), c["name"]).strip(),
                     "corn": corn_pin(static_cards["corn"].get(c["fips"]), c["name"]).strip()},
        }
        if barns and near_of:
            out["counties"][c["fips"]]["barns"] = near_of(c["fips"])
    return out
