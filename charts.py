"""The 'Why Use Our Apps' charts, drawn as inline SVG in plain Python (no libraries).

Each story in content/stories.json names a chart kind; draw(story) returns the SVG, and
table(story) returns the same numbers as an HTML table (for screen readers, and for anyone
who'd rather read numbers than a picture).

Why SVG written by hand? The site is static and has no build tools beyond Python's standard
library. An SVG is just text: shapes with coordinates. It scales to any screen, prints sharply,
and search engines can read its labels.

Chart rules followed here (from the data-viz guide):
- Colors do one job: blue = the first series, orange = the second (a pair checked for color
  blindness). Words are never colored; a small swatch beside them carries the identity.
- Thin bars with rounded ends, growing from a single baseline; hairline, solid gridlines.
- Labels on the few values that tell the story, not on every point.
- Hover any bar or point for its exact value (the SVG <title> tooltip).
"""

from html import escape

BLUE, ORANGE = "#2a78d6", "#eb6834"
W, H = 480, 280  # drawn small so its text stays readable when the chart is half a page wide
LEFT, RIGHT, TOP, BOTTOM = 44, 12, 22, 40  # room for axis labels


def e(x) -> str:
    return escape(str(x), quote=True)


def fmt(v: float, digits: int = 0) -> str:
    s = f"{v:.{digits}f}"
    return "0" if s in ("-0", "-0.0") else s


def bar(x: float, w: float, y0: float, y1: float, color: str, tip: str, r: float = 4) -> str:
    """A bar from baseline y0 to y1, square at the baseline, 4px rounded at the data end."""
    top, bottom = min(y0, y1), max(y0, y1)
    h = bottom - top
    if h < 0.5:
        return f'<rect x="{x:.1f}" y="{y0 - 0.5:.1f}" width="{w:.1f}" height="1" fill="{color}"><title>{e(tip)}</title></rect>'
    r = min(r, h, w / 2)
    if y1 < y0:  # grows up: round the top corners
        d = (f"M{x:.1f},{bottom:.1f} V{top + r:.1f} Q{x:.1f},{top:.1f} {x + r:.1f},{top:.1f} "
             f"H{x + w - r:.1f} Q{x + w:.1f},{top:.1f} {x + w:.1f},{top + r:.1f} V{bottom:.1f} Z")
    else:  # grows down: round the bottom corners
        d = (f"M{x:.1f},{top:.1f} V{bottom - r:.1f} Q{x:.1f},{bottom:.1f} {x + r:.1f},{bottom:.1f} "
             f"H{x + w - r:.1f} Q{x + w:.1f},{bottom:.1f} {x + w:.1f},{bottom - r:.1f} V{top:.1f} Z")
    return f'<path d="{d}" fill="{color}"><title>{e(tip)}</title></path>'


class Frame:
    """Maps data values to pixels and draws the recessive grid and axis labels."""

    def __init__(self, ymin: float, ymax: float, ticks: list[float], unit: str = ""):
        self.ymin, self.ymax, self.ticks, self.unit = ymin, ymax, ticks, unit
        self.x0, self.x1, self.y0, self.y1 = LEFT, W - RIGHT, TOP, H - BOTTOM

    def y(self, v: float) -> float:
        return self.y1 - (v - self.ymin) / (self.ymax - self.ymin) * (self.y1 - self.y0)

    def grid(self) -> str:
        out = []
        for t in self.ticks:
            y = self.y(t)
            out.append(f'<line x1="{self.x0}" x2="{self.x1}" y1="{y:.1f}" y2="{y:.1f}" class="grid{" zero" if t == 0 else ""}"/>')
            out.append(f'<text x="{self.x0 - 8}" y="{y + 4:.1f}" text-anchor="end" class="tick">{fmt(t)}{self.unit}</text>')
        return "".join(out)


def svg(inner: str, label: str) -> str:
    return (f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="{e(label)}" '
            f'preserveAspectRatio="xMidYMid meet">{inner}</svg>')


def legend(names: list[str]) -> str:
    """Series 1 is blue, series 2 orange (the .s1/.s2 swatch classes in site.css)."""
    items = "".join(f'<span class="key"><span class="swatch s{i + 1}"></span>{e(n)}</span>'
                    for i, n in enumerate(names))
    return f'<div class="legend">{items}</div>'


# --- the chart kinds ------------------------------------------------------------------------------


def seasonal(s: dict) -> str:
    """Grouped bars around zero: % above or below the trend, by month, for two weights."""
    f = Frame(-8, 8, [-8, -4, 0, 4, 8], "%")
    band = (f.x1 - f.x0) / 12
    bw = min(16, (band - 10) / 2)
    parts = [f.grid()]
    colors = [BLUE, ORANGE]
    for m, month in enumerate(s["months"]):
        cx = f.x0 + band * (m + 0.5)
        for k, series in enumerate(s["series"]):
            pct = (series["index"][m] - 1) * 100
            x = cx - bw - 1 if k == 0 else cx + 1  # 2px gap between the pair
            tip = f'{month}, {series["name"]}: {pct:+.1f}% vs trend'
            parts.append(bar(x, bw, f.y(0), f.y(pct), colors[k], tip))
        parts.append(f'<text x="{cx:.1f}" y="{H - BOTTOM + 18}" text-anchor="middle" class="tick">{e(month)}</text>')
    # Label the story: calves' high (March) and low (October).
    calves = [(v - 1) * 100 for v in s["series"][0]["index"]]
    for m in (calves.index(max(calves)), calves.index(min(calves))):
        v = calves[m]
        cx = f.x0 + band * (m + 0.5) - bw / 2 - 1
        y = f.y(v) + (-6 if v > 0 else 14)
        parts.append(f'<text x="{cx:.1f}" y="{y:.1f}" text-anchor="middle" class="value">{v:+.0f}%</text>')
    return svg("".join(parts), s["chart_title"]) + legend([x["name"] for x in s["series"]])


def keep_rate(s: dict) -> str:
    """Columns: chance (of 100) of reaching the herd goal, by keep-rate."""
    f = Frame(0, 100, [0, 25, 50, 75, 100])
    n = len(s["keep_pct"])
    band = (f.x1 - f.x0) / n
    bw = min(24, band - 12)
    parts = [f.grid()]
    for i, (k, v) in enumerate(zip(s["keep_pct"], s["reach_pct"])):
        x = f.x0 + band * i + (band - bw) / 2
        parts.append(bar(x, bw, f.y(0), f.y(v), BLUE, f"Keep {k}%: reaches the goal in {v:.0f} of 100 futures"))
        if k >= 70:
            parts.append(f'<text x="{x + bw / 2:.1f}" y="{f.y(v) - 6:.1f}" text-anchor="middle" class="value">{v:.0f}</text>')
        parts.append(f'<text x="{x + bw / 2:.1f}" y="{H - BOTTOM + 18}" text-anchor="middle" class="tick">{k}%</text>')
    parts.append(f'<text x="{(f.x0 + f.x1) / 2:.1f}" y="{H - 4}" text-anchor="middle" class="axis">Share of heifer calves kept each fall</text>')
    return svg("".join(parts), s["chart_title"])


def ladder(s: dict) -> str:
    """Horizontal bars: the model's score as each kind of information is added."""
    rows = len(s["steps"])
    h = 34 * rows + 40
    x0, x1 = 170, W - 70
    scale = lambda v: x0 + v / 0.8 * (x1 - x0)  # axis 0 to 0.8
    parts = []
    for t in (0, 0.2, 0.4, 0.6, 0.8):
        x = scale(t)
        parts.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="8" y2="{h - 28}" class="grid{" zero" if t == 0 else ""}"/>')
        parts.append(f'<text x="{x:.1f}" y="{h - 10}" text-anchor="middle" class="tick">{t:.1f}</text>')
    prev = None
    for i, (step, v) in enumerate(zip(s["steps"], s["r2"])):
        y = 12 + 34 * i
        tip = f"{step}: R² {v:.3f}" + (f" ({v - prev:+.3f})" if prev is not None else "")
        # horizontal bar: square at the zero line, rounded at the value end
        w = scale(v) - x0
        r = 4
        d = (f"M{x0},{y} H{x0 + w - r:.1f} Q{x0 + w:.1f},{y} {x0 + w:.1f},{y + r} "
             f"V{y + 18 - r} Q{x0 + w:.1f},{y + 18} {x0 + w - r:.1f},{y + 18} H{x0} Z")
        parts.append(f'<path d="{d}" fill="{BLUE}"><title>{e(tip)}</title></path>')
        parts.append(f'<text x="{x0 - 10}" y="{y + 13}" text-anchor="end" class="label">{e(step)}</text>')
        gain = f" ({v - prev:+.2f})" if prev is not None else ""
        parts.append(f'<text x="{x0 + w + 6:.1f}" y="{y + 13}" class="value">{v:.2f}{gain if i == 1 else ""}</text>')
        prev = v
    return (f'<svg class="chart" viewBox="0 0 {W} {h}" role="img" aria-label="{e(s["chart_title"])}">'
            + "".join(parts) + "</svg>")


def hire_wait(s: dict) -> str:
    """A line: how often custom hire is the cheaper choice, by days the crew arrives late."""
    f = Frame(0, 100, [0, 25, 50, 75, 100], "%")
    days, pct = s["delay_days"], s["custom_cheapest_pct"]
    xmax = max(days)
    x = lambda d: f.x0 + d / xmax * (f.x1 - f.x0)
    parts = [f.grid()]
    for d in range(0, xmax + 1, 4):
        parts.append(f'<text x="{x(d):.1f}" y="{H - BOTTOM + 18}" text-anchor="middle" class="tick">{d}</text>')
    parts.append(f'<text x="{(f.x0 + f.x1) / 2:.1f}" y="{H - 4}" text-anchor="middle" class="axis">Days the custom crew arrives after you could start</text>')
    points = " ".join(f"{x(d):.1f},{f.y(v):.1f}" for d, v in zip(days, pct))
    parts.append(f'<polyline points="{points}" fill="none" stroke="{BLUE}" stroke-width="2" stroke-linejoin="round"/>')
    for d, v in zip(days, pct):
        parts.append(f'<circle cx="{x(d):.1f}" cy="{f.y(v):.1f}" r="4" fill="{BLUE}" stroke="#fff" stroke-width="2">'
                     f'<title>Crew {d} days later: hire is cheaper in {v:.0f}% of futures</title></circle>')
    for d, v, dy, anchor in ((12, 100, 20, "end"), (16, 62.3, -4, "start"), (28, 0, -12, "end")):
        label = {12: "100% up to 12 days", 16: "62% at 16 days", 28: "0% from 22 days on"}[d]
        parts.append(f'<text x="{x(d) + (8 if anchor == "start" else 0):.1f}" y="{f.y(v) + dy:.1f}" '
                     f'text-anchor="{anchor}" class="value">{label}</text>')
    return svg("".join(parts), s["chart_title"])


def skill_by_date(s: dict) -> str:
    """Columns: forecast skill (0 = no better than assuming a normal year, 1 = perfect) by forecast
    date. A date with no skill gets no column, just the word "none" on the baseline."""
    f = Frame(0, 1, [])
    n = len(s["dates"])
    band = (f.x1 - f.x0) / n
    bw = min(28, band - 14)
    parts = []
    for t in (0, 0.25, 0.5, 0.75, 1):
        y = f.y(t)
        parts.append(f'<line x1="{f.x0}" x2="{f.x1}" y1="{y:.1f}" y2="{y:.1f}" class="grid{" zero" if t == 0 else ""}"/>')
        parts.append(f'<text x="{f.x0 - 8}" y="{y + 4:.1f}" text-anchor="end" class="tick">{t:g}</text>')
    for i, (d, v) in enumerate(zip(s["dates"], s["skill"])):
        cx = f.x0 + band * (i + 0.5)
        if v is None:
            parts.append(f'<text x="{cx:.1f}" y="{f.y(0) - 6:.1f}" text-anchor="middle" class="value">none</text>'
                         f'<title>{e(d)}: no better than assuming a normal year</title>')
        else:
            parts.append(bar(cx - bw / 2, bw, f.y(0), f.y(v), BLUE, f"{d}: skill {v:.2f}"))
            parts.append(f'<text x="{cx:.1f}" y="{f.y(v) - 6:.1f}" text-anchor="middle" class="value">{v:.2f}</text>')
        parts.append(f'<text x="{cx:.1f}" y="{H - BOTTOM + 18}" text-anchor="middle" class="tick">{e(d)}</text>')
    parts.append(f'<text x="{(f.x0 + f.x1) / 2:.1f}" y="{H - 4}" text-anchor="middle" class="axis">Date the forecast is made</text>')
    return svg("".join(parts), s["chart_title"])


KINDS = {"seasonal": seasonal, "keep_rate": keep_rate, "ladder": ladder, "hire_wait": hire_wait,
         "skill_by_date": skill_by_date}


def draw(story: dict) -> str:
    return KINDS[story["chart"]](story)


def table(story: dict) -> str:
    """The chart's numbers as a plain table, inside a 'Show the numbers' fold."""
    k = story["chart"]
    if k == "seasonal":
        head = ["Month"] + [x["name"] for x in story["series"]]
        rows = [[m] + [f'{(x["index"][i] - 1) * 100:+.1f}%' for x in story["series"]]
                for i, m in enumerate(story["months"])]
    elif k == "keep_rate":
        head = ["Heifer calves kept", "Futures reaching the goal (of 100)"]
        rows = [[f"{a}%", f"{b:.1f}"] for a, b in zip(story["keep_pct"], story["reach_pct"])]
    elif k == "ladder":
        head = ["Information added", "Score (R²)"]
        rows = [[a, f"{b:.3f}"] for a, b in zip(story["steps"], story["r2"])]
    elif k == "skill_by_date":
        head = ["Forecast made on", "Skill (0 = normal, 1 = perfect)", "Typical miss, % of normal"]
        rows = [[d, "none" if v is None else f"{v:.2f}", f"{m:.1f}%"]
                for d, v, m in zip(story["dates"], story["skill"], story["typical_miss_pct"])]
    else:
        head = ["Days the crew arrives later", "Custom hire cheaper in"]
        rows = [[str(a), f"{b:g}%"] for a, b in zip(story["delay_days"], story["custom_cheapest_pct"])]
    th = "".join(f"<th>{e(h)}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{e(c)}</td>" for c in r) + "</tr>" for r in rows)
    return (f'<details class="numbers"><summary>Show the numbers</summary><div class="table-scroll">'
            f'<table class="results"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div></details>')


def barn_history(points: list[tuple[str, float, float, float]]) -> str:
    """One barn's 550 lb steer price, week by week: a dot for the price, a whisker for the range 8 in
    10 sales fell in, and a thin line joining the dots. The same barn every week, so the weeks compare."""
    f = None
    lows, highs = [p[2] for p in points], [p[3] for p in points]
    lo, hi = min(lows), max(highs)
    pad = (hi - lo) * 0.15 or 10
    lo, hi = lo - pad, hi + pad
    step = 10 if hi - lo < 80 else 25 if hi - lo < 200 else 50
    ticks = [t for t in range(int(lo // step * step), int(hi) + step, step) if lo <= t <= hi]
    f = Frame(lo, hi, ticks)
    n = len(points)
    xs = [f.x0 + 20 + i * (f.x1 - f.x0 - 40) / max(n - 1, 1) for i in range(n)]
    parts = [f.grid()]
    line = " ".join(f"{x:.1f},{f.y(p[1]):.1f}" for x, p in zip(xs, points))
    parts.append(f'<polyline points="{line}" fill="none" stroke="{BLUE}" stroke-width="2" stroke-linejoin="round" opacity=".5"/>')
    for i, (x, (when, price, low, high)) in enumerate(zip(xs, points)):
        parts.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{f.y(low):.1f}" y2="{f.y(high):.1f}" stroke="#86b6ef" stroke-width="3" stroke-linecap="round"/>')
        parts.append(f'<circle cx="{x:.1f}" cy="{f.y(price):.1f}" r="5" fill="{BLUE}" stroke="#fff" stroke-width="2">'
                     f'<title>{e(when)}: ${price:,.0f}/cwt (8 in 10 sales ${low:,.0f} to ${high:,.0f})</title></circle>')
        step_lbl = -(-n // 5)
        if i == n - 1 or (i % step_lbl == 0 and n - 1 - i >= step_lbl):  # ~5 date labels, the latest always, never crowded
            parts.append(f'<text x="{x:.1f}" y="{H - BOTTOM + 18}" text-anchor="middle" class="tick">{e(when)}</text>')
    last = points[-1]
    parts.append(f'<text x="{xs[-1]:.1f}" y="{f.y(last[3]) - 8:.1f}" text-anchor="end" class="value">${last[1]:,.0f}</text>')
    return svg("".join(parts), "550 lb steer price by week, with the range 8 in 10 sales fell in")


MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
               "November", "December"]


def season_order(season: dict) -> list[int]:
    """Calendar months left to right. With a this-season line, the axis ends at its newest month
    (Oct ... Sep), so the line runs left to right without jumping back from Dec to Jan."""
    recent = season.get("this_season") or []
    if not recent:
        return list(range(1, 13))
    last = int(recent[-1]["month"][5:7])
    return [(last + i) % 12 + 1 for i in range(12)]


def best_months(season: dict, barn_name: str) -> str:
    """The typical year (dot = typical level, bar = 95% range) and this season (one line) on one scale:
    % above or below an average month. Months the barn doesn't sell stay empty, labeled in grey."""
    order = season_order(season)
    typical = {m["month"]: m for m in season["typical"]}
    recent = {int(r["month"][5:7]): r for r in season.get("this_season") or []}
    values = [(m["low"] - 1) * 100 for m in typical.values()] + [(m["high"] - 1) * 100 for m in typical.values()]
    values += [(r["ratio"] - 1) * 100 for r in recent.values()]
    top = max(10, 5 * -(-max(abs(v) for v in values) // 5)) if values else 10
    f = Frame(-top, top, [t for t in range(int(-top), int(top) + 1, 5)], "%")
    band = (f.x1 - f.x0) / 12
    x = {m: f.x0 + band * (i + 0.5) for i, m in enumerate(order)}
    parts = [f.grid()]
    for m in order:
        cls = "tick" if m in typical or m in recent else "tick faint"  # grey: no sales that month, ever or lately
        parts.append(f'<text x="{x[m]:.1f}" y="{H - BOTTOM + 18}" text-anchor="middle" class="{cls}">{MONTH_ABBR[m - 1]}</text>')
    for m, t in typical.items():
        pct, lo, hi = (t["index"] - 1) * 100, (t["low"] - 1) * 100, (t["high"] - 1) * 100
        tip = f"{MONTH_ABBR[m - 1]}, typical year: {pct:+.1f}% vs an average month (95% range {lo:+.1f}% to {hi:+.1f}%)"
        parts.append(f'<line x1="{x[m]:.1f}" x2="{x[m]:.1f}" y1="{f.y(lo):.1f}" y2="{f.y(hi):.1f}" stroke="#86b6ef" '
                     f'stroke-width="6" stroke-linecap="round"><title>{e(tip)}</title></line>')
        parts.append(f'<circle cx="{x[m]:.1f}" cy="{f.y(pct):.1f}" r="4" fill="{BLUE}" stroke="#fff" stroke-width="2">'
                     f'<title>{e(tip)}</title></circle>')
    # This season: one line, broken where a month had no sale.
    run: list[str] = []
    runs = []
    for m in order:
        if m in recent:
            run.append(f"{x[m]:.1f},{f.y((recent[m]['ratio'] - 1) * 100):.1f}")
        elif run:
            runs.append(run)
            run = []
    if run:
        runs.append(run)
    for r in runs:
        if len(r) > 1:
            parts.append(f'<polyline points="{" ".join(r)}" fill="none" stroke="{ORANGE}" stroke-width="2" stroke-linejoin="round"/>')
    for m, r in recent.items():
        pct = (r["ratio"] - 1) * 100
        month = f"{MONTH_ABBR[m - 1]} {r['month'][:4]}"
        parts.append(f'<circle cx="{x[m]:.1f}" cy="{f.y(pct):.1f}" r="4" fill="{ORANGE}" stroke="#fff" stroke-width="2">'
                     f'<title>{e(month)}, this season: {pct:+.1f}% vs this year\'s trend line</title></circle>')
    label = f"{season['label']} at {barn_name}: typical year and this season, % vs an average month"
    names = ["Typical year (dot) with its 95% range (bar)"] + (["This season, last 12 months"] if recent else [])
    return svg("".join(parts), label) + legend(names)


def best_months_table(season: dict) -> str:
    """The best-months chart as a plain table inside a 'Show the numbers' fold."""
    typical = {m["month"]: m for m in season["typical"]}
    recent = {int(r["month"][5:7]): r for r in season.get("this_season") or []}
    rows = []
    for m in season_order(season):
        t, r = typical.get(m), recent.get(m)
        rows.append([MONTH_ABBR[m - 1],
                     f"{(t['index'] - 1) * 100:+.1f}%" if t else "no sales",
                     f"{(t['low'] - 1) * 100:+.1f}% to {(t['high'] - 1) * 100:+.1f}%" if t else "",
                     f"{(r['ratio'] - 1) * 100:+.1f}% ({MONTH_ABBR[m - 1]} {r['month'][:4]})" if r else ""])
    head = ["Month", "Typical year", "95% range", "This season"]
    th = "".join(f"<th>{e(h)}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{e(c)}</td>" for c in row) + "</tr>" for row in rows)
    return (f'<details class="numbers"><summary>Show the numbers</summary><div class="table-scroll">'
            f'<table class="results"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div></details>')
