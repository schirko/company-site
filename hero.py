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


def e(x) -> str:
    return escape(str(x), quote=True)


# --- tiny charts (inline SVG) --------------------------------------------------------------------


def range_bar(low: float, value: float, high: float | None, lo: float, hi: float,
              labels: tuple[str, str, str]) -> str:
    """A bullet line: a pale band from low to high (or low to value), a dot at the value."""
    w, h = 260, 44
    x = lambda v: 8 + (v - lo) / (hi - lo) * (w - 16)
    right = high if high is not None else value
    parts = [
        f'<line x1="8" x2="{w - 8}" y1="14" y2="14" stroke="{GREY}" stroke-width="2" stroke-linecap="round"/>',
        f'<line x1="{x(low):.1f}" x2="{x(right):.1f}" y1="14" y2="14" stroke="{BLUE_LIGHT}" stroke-width="10" stroke-linecap="round"/>',
        f'<circle cx="{x(value):.1f}" cy="14" r="7" fill="{BLUE}" stroke="#fff" stroke-width="2"/>',
        f'<text x="{x(low):.1f}" y="38" text-anchor="middle" class="tick">{e(labels[0])}</text>',
    ]
    if high is not None:
        parts.append(f'<text x="{x(high):.1f}" y="38" text-anchor="middle" class="tick">{e(labels[2])}</text>')
    else:
        parts.append(f'<text x="{x(value):.1f}" y="38" text-anchor="middle" class="tick">{e(labels[1])}</text>')
    return f'<svg class="mini" viewBox="0 0 {w} {h}" aria-hidden="true">{"".join(parts)}</svg>'


def month_strip(index: list[float], current: int) -> str:
    """Twelve small bars around zero (% vs trend); this month in blue, the rest grey."""
    w, h, mid = 260, 70, 32
    band = (w - 8) / 12
    parts = [f'<line x1="4" x2="{w - 4}" y1="{mid}" y2="{mid}" stroke="#b9b6ad" stroke-width="1"/>']
    for m, v in enumerate(index):
        pct = (v - 1) * 100
        bh = abs(pct) * 4  # 4 px per percentage point: +/-6% fits
        x = 4 + band * m + band * 0.2
        bw = band * 0.6
        y = mid - bh if pct > 0 else mid
        color = BLUE if m == current else "#cfd6de"
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{max(bh, 1):.1f}" rx="2" fill="{color}"/>')
        parts.append(f'<text x="{x + bw / 2:.1f}" y="{h - 4}" text-anchor="middle" class="tick{" now" if m == current else ""}">'
                     f'{"JFMAMJJASOND"[m]}</text>')
    return f'<svg class="mini" viewBox="0 0 {w} {h}" aria-hidden="true">{"".join(parts)}</svg>'


def day_squares(typical: float, wet: float, total: int = 61) -> str:
    """61 squares, one per day Oct 1 - Nov 30: dark = workable in a wet fall, light = the extra
    workable days a typical fall adds, grey = too wet."""
    cols, size, gap = 21, 10, 2.4
    rows = -(-total // cols)
    w, h = cols * (size + gap), rows * (size + gap)
    parts = []
    for d in range(total):
        c = BLUE if d < round(wet) else BLUE_LIGHT if d < round(typical) else GREY
        x, y = (d % cols) * (size + gap), (d // cols) * (size + gap)
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{size}" height="{size}" rx="2" fill="{c}"/>')
    return f'<svg class="mini days" viewBox="0 0 {w:.0f} {h:.0f}" aria-hidden="true">{"".join(parts)}</svg>'


# --- the panel -----------------------------------------------------------------------------------


def tile(href: str, callout: str, label: str, headline: str, chart: str, note: str, extra_class: str = "") -> str:
    return f"""        <a class="live-tile{extra_class}" href="{e(href)}">
          <span class="callout">{e(callout)}</span>
          <span class="live-label">{e(label)}</span>
          <span class="live-headline">{e(headline)}</span>
          {chart}
          <span class="live-note">{e(note)}</span>
        </a>"""


def money(x: float) -> str:
    return f"${x:,.0f}"


def panel(week: dict, stories: list[dict], nice_date) -> str:
    place = week["place"]
    where = f'{place["county"]}, {place["state_name"]}'
    cards = week["cards"]
    tiles = []

    herd = cards.get("herd-planner")
    if herd:
        sold = date.fromisoformat(herd["as_of"])
        tiles.append(tile(
            "herd-planner.html", "8 in 10 sales land in this range", "550 lb steer, this week",
            f'{money(herd["value"])}/cwt',
            range_bar(herd["low"], herd["value"], herd["high"], herd["low"] * 0.97, herd["high"] * 1.03,
                      (money(herd["low"]), "", money(herd["high"]))),
            f'About {money(herd["value"] * 5.5)} a head at {herd["market"]}, sale of {sold:%b} {sold.day}.'))
    else:
        tiles.append(tile(
            "herd-planner.html", "USDA auction reports", "550 lb steer, this week", "No fresh price",
            "", f'No sale barn near {place["state_name"]} reported in the last three weeks. Prices update every Friday.',
            " quiet"))

    season = next((s for s in stories if s["chart"] == "seasonal"), None)
    if season:
        m = date.fromisoformat(week["date"]).month - 1
        calves = season["series"][0]["index"]
        pct = (calves[m] - 1) * 100
        tiles.append(tile(
            "herd-planner.html#calf-season", "Oklahoma City sales, 2021-2026", f'Calves in {season["months"][m]}, vs the yearly trend',
            f"{pct:+.0f}%".replace("-", "\u2212"), month_strip(calves, m),
            "Lowest in October and November, highest in March. Tendencies, not guarantees."))

    corn = cards.get("corn-yield-predictor")
    if corn:
        tiles.append(tile(
            "corn-yield-predictor.html", "USDA county yields since 2000", corn["label"], corn["headline"],
            range_bar(corn["low"], corn["value"], None, corn["low"] * 0.94, corn["value"] * 1.04,
                      (f'{corn["low"]:.0f} low', f'{corn["value"]:.0f} trend', "")),
            f'Trend for {where}. In 1 year in 10 it falls below {corn["low"]:.0f} bu/acre.'))

    days = cards.get("farm-equipment-planner")
    if days:
        tiles.append(tile(
            "farm-equipment-planner.html", "Real falls on record, day by day", days["label"], days["headline"],
            day_squares(days["value"], days["low"]),
            f'Dark: workable even in a wet fall ({days["low"]:.0f}). Light: extra days in a typical fall.'))

    return f"""    <div class="live" id="this-week">
      <p class="live-head"><span class="live-dot" aria-hidden="true"></span> New every Friday &middot; week of {nice_date(week["date"])}</p>
      <h2>This Week: {e(where)}</h2>
      <div class="live-grid">
{chr(10).join(tiles)}
      </div>
      <p class="live-foot">One farm county each week, real numbers from each app.
        <a href="methods.html">How we test them</a></p>
    </div>"""
