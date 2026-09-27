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


def herd_tile(herd: dict | None, state_name: str, barn_href=None) -> str:
    """barn_href(slug) gives that barn's page on the site, or None; the tile then links there."""
    if not herd:
        return tile("herd-planner.html", "USDA auction reports", "550 lb steer, this week", "No fresh price", "",
                    f"No sale barn near {state_name} reported in the last three weeks. Prices update every Friday.",
                    " quiet", slot="herd")
    sold = date.fromisoformat(herd["as_of"])
    href = (barn_href(herd.get("market_slug")) if barn_href and herd.get("market_slug") else None) or "herd-planner.html"
    return tile(
        href, "8 in 10 sales land in this range", "550 lb steer, this week",
        f'{money(herd["value"])}/cwt',
        range_bar(herd["low"], herd["value"], herd["high"], herd["low"] * 0.97, herd["high"] * 1.03,
                  (money(herd["low"]), "", money(herd["high"])), marker="this sale"),
        f'About {money(herd["value"] * 5.5)} a head at {herd["market"]}, sale of {sold:%b} {sold.day}.', slot="herd")


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


PICKER = """      <form class="live-pick" id="live-pick" hidden>
        <label>State <select name="state"></select></label>
        <label>County <select name="county"></select></label>
        <button type="submit" class="btn small">Show</button>
        <button type="button" class="linklike live-pick-reset">County of the week</button>
      </form>"""


def panel(week: dict, stories: list[dict], nice_date, barn_href=None) -> str:
    place = week["place"]
    where = f'{place["county"]}, {place["state_name"]}'
    cards = week["cards"]
    season = next((s for s in stories if s["chart"] == "seasonal"), None)
    tiles = [herd_tile(cards.get("herd-planner"), place["state_name"], barn_href)]
    if season:
        tiles.append(calves_tile(season, date.fromisoformat(week["date"])))
    tiles.append(corn_tile(cards.get("corn-yield-predictor"), where))
    tiles.append(days_tile(cards.get("farm-equipment-planner"), where))
    # The picker's button and form start hidden: panel.js shows them, so a browser without
    # JavaScript sees the county of the week and nothing that doesn't work.
    return f"""    <div class="live" id="this-week" data-week-place="{e(where)}">
      <div class="live-top">
        <p class="live-head"><span class="live-dot" aria-hidden="true"></span> New every Friday &middot; week of {nice_date(week["date"])}</p>
        <button type="button" class="live-pick-open" hidden aria-expanded="false" aria-controls="live-pick">See your county</button>
      </div>
      <h2><span class="live-title">This Week</span>: <span class="live-where">{e(where)}</span></h2>
{PICKER}
      <div class="live-grid" aria-live="polite">
{chr(10).join(tiles)}
      </div>
      <p class="live-foot">One farm county each week, real numbers from each app.
        <a href="methods.html">How we test them</a></p>
    </div>
    <script src="panel.js" defer></script>"""


def panel_data(week: dict, counties: list[dict], static_cards: dict, not_covered: dict, state_names: dict,
               barn_href=None) -> dict:
    """Everything the county picker needs, each tile already drawn by the same functions as the page,
    so a picked county looks exactly like the county of the week. build.py writes it to
    docs/panel-data.json; panel.js reads it only when a visitor asks for their county."""
    by_state = week.get("herd_by_state") or {}
    out = {"format": 1, "week": week["week"], "default": week["place"]["fips"],
           "states": {code: state_names[code] for code in sorted({c["state"] for c in counties})},
           "herd": {code: herd_tile(by_state.get(code), state_names[code], barn_href) for code in state_names},
           "counties": {}}
    for c in counties:
        where = f'{c["name"]}, {state_names[c["state"]]}'
        out["counties"][c["fips"]] = {
            "name": c["name"], "state": c["state"],
            "corn": corn_tile(static_cards["corn"].get(c["fips"]), where, not_covered["corn"]),
            "days": days_tile(static_cards["days"].get(c["fips"]), where, not_covered["days"]),
        }
    return out
