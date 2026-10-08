"""The weekly stat cards: one farm county each week, with a real number from each app.

    python cards.py refresh      # pick this week's place, ask Herd Planner for prices, save it
    python build.py              # then rebuild the site with the new numbers

A GitHub Action runs both every Friday (.github/workflows/weekly-cards.yml) and commits the
result, so the site gets new numbers each week with nobody at a keyboard.

Where the numbers come from:

* content/cards/corn-yield-predictor.json and farm-equipment-planner.json: county cards exported
  by those two apps (their numbers change once a year). `refresh` copies newer ones in from the
  sibling project folders when they're there (on your computer; not on GitHub's machine).
* Herd Planner: this week's 550 lb steer price, asked live from its public GET /suite/summary.
  It sleeps on Render's free plan, so `refresh` waits for it to wake (up to about 4 minutes).
  Sample prices are never published.
* Grazing Planner: this season's grass against normal for the county (Nebraska counties only),
  asked live from its public GET /api/season and POST /api/plan (the same answer anyone gets on
  its page). Also on Render's free plan, so it gets the same wait. Shown on the home page's app tile.

Each week is saved in content/cards/weeks.json (newest first) with a copy of every card, so a
number on the site never changes after the week it was shown, and the app pages can list past weeks.

The place of the week: every county both the Yield Predictor and the Equipment Planner cover, in a
fixed shuffled order (by a hash of its FIPS code, so neighbors don't come one after another), one
per week. 88 counties means about 21 months before a county comes around again.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CARDS = ROOT / "content" / "cards"
WEEKS = CARDS / "weeks.json"
BARNS_FILE = CARDS / "barns.json"  # every sale barn's weekly price sheet, newest week first
HERD, CORN, EQUIP, GRAZE = "herd-planner", "corn-yield-predictor", "farm-equipment-planner", "grazing-planner"
STATIC_APPS = (CORN, EQUIP)
SIBLINGS = {  # where each app's exported card file lives, next to this project
    CORN: ROOT.parent / "crop-yield-predictor" / "data" / "processed" / "suite_card.json",
    EQUIP: ROOT.parent / "farm-equipment-planner" / "regional" / "data" / "suite_card.json",
}
HERD_PLANNER_URL = os.getenv("HERD_PLANNER_URL", "https://herd-planner.onrender.com")
GRAZING_PLANNER_URL = os.getenv("GRAZING_PLANNER_URL", "https://grazing-planner.onrender.com")
WAKE_TRIES, WAKE_WAIT, TIMEOUT = 8, 30, 30  # seconds: Render's free plan takes up to a minute to wake
FRESH_DAYS = 21  # an older steer price isn't "this week" and isn't shown
KEEP_WEEKS = 520  # ten years of history; the pages show the latest few
STATE_NAMES = {"NE": "Nebraska", "IA": "Iowa"}
STATE_OF_FIPS = {"31": "NE", "19": "IA"}


# --- the county files ---------------------------------------------------------------------------


def load_static(app_id: str) -> dict:
    return json.loads((CARDS / f"{app_id}.json").read_text(encoding="utf-8"))


def copy_from_siblings() -> list[str]:
    """Copy each app's newest exported card file in, when the project is next to this one."""
    said = []
    for app_id, src in SIBLINGS.items():
        if not src.exists():
            continue
        data = json.loads(src.read_text(encoding="utf-8"))
        if data.get("format") == 1 and data.get("cards"):
            shutil.copyfile(src, CARDS / f"{app_id}.json")
            said.append(f"{app_id}: copied {len(data['cards'])} counties from {src.parent.name}")
    return said


# --- the place of the week ----------------------------------------------------------------------


def week_id(day: date) -> str:
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def rotation() -> list[str]:
    """Counties with numbers from both county apps, in a fixed shuffled order."""
    both = set(load_static(CORN)["cards"]) & set(load_static(EQUIP)["cards"])
    return sorted(both, key=lambda fips: hashlib.sha256(fips.encode()).hexdigest())


def place_for(day: date) -> dict:
    order = rotation()
    weeks_since = (day - date(2026, 1, 5)).days // 7  # 2026-01-05 is a Monday: week 0
    fips = order[weeks_since % len(order)]
    state = STATE_OF_FIPS[fips[:2]]
    county = load_static(CORN)["cards"][fips]["detail"].split(",")[0]  # "Hall County"
    return {"fips": fips, "state": state, "county": county, "state_name": STATE_NAMES[state]}


# --- Herd Planner -------------------------------------------------------------------------------


def _get(url: str, body: dict | None = None) -> tuple[int, dict]:
    """One HTTP GET (or a POST of JSON when `body` is given) returning (status, JSON). Tests replace this."""
    headers = {"User-Agent": "company-site weekly cards"}
    data = None
    if body is not None:
        data, headers["Content-Type"] = json.dumps(body).encode("utf-8"), "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        return err.code, {}


def fetch_herd(state: str, wait=time.sleep) -> tuple[dict | None, str]:
    """(card, note). Tries while Render wakes the app; never returns sample prices."""
    url = f"{HERD_PLANNER_URL.rstrip('/')}/suite/summary?" + urllib.parse.urlencode({"state": state})
    return _ask(url, wait)


def fetch_barns(wait=time.sleep) -> tuple[dict | None, str]:
    """(every barn's price sheet, note) from Herd Planner's GET /suite/barns."""
    return _ask(f"{HERD_PLANNER_URL.rstrip('/')}/suite/barns", wait)


def _ask(url: str, wait, app: str = "Herd Planner", body: dict | None = None) -> tuple[dict | None, str]:
    last = ""
    for attempt in range(WAKE_TRIES):
        try:
            status, answer = _get(url, body) if body is not None else _get(url)
        except (OSError, ValueError) as err:  # timeouts, refused connections, a half-awake server
            status, answer, last = 0, {}, f"no answer ({err.__class__.__name__})"
        if status == 200:
            if answer.get("is_sample"):
                return None, "Herd Planner only has sample prices; not published"
            return answer, "ok"
        if status:
            last = f"HTTP {status}"
            if status in (404, 409, 422):  # a real answer: waiting won't change it
                break
        if attempt + 1 < WAKE_TRIES:
            wait(WAKE_WAIT)
    return None, f"{app} didn't answer: {last}"


# --- Grazing Planner ----------------------------------------------------------------------------

GRASS_SOURCE = "Rangeland Analysis Platform (USDA Agricultural Research Service) and NASA POWER weather, via the Grazing Planner"
GRASS_METHOD = ("The Grazing Planner's own answer for the county's grassland on its latest check date: grass grown so far "
                "plus the forecast for the rest of the season, against the county's average over the 10 seasons before. "
                "The range is where 8 in 10 seasons landed around forecasts made on the same date.")


def fetch_grass(fips: str, wait=time.sleep) -> tuple[dict | None, str]:
    """(card, note): this season's grass against normal for a county, from the Grazing Planner.
    Only Nebraska counties are covered; others get (None, reason) without asking twice."""
    base = GRAZING_PLANNER_URL.rstrip("/")
    season, note = _ask(f"{base}/api/season", wait, app="Grazing Planner")
    if not season:
        return None, note
    if fips not in {c["fips"] for c in season.get("counties", [])}:
        return None, "the Grazing Planner doesn't cover this county"
    ask = {"fips": fips, "acres": 1000, "kind": season["kinds"][0], "animal": season["animals"][0], "head": 1}
    answer, note = _ask(f"{base}/api/plan", wait, app="Grazing Planner", body=ask)
    return (grass_card(answer, season) if answer else None), note


def grass_words(point: float) -> str:
    """-0.081 -> "8% below normal"; within 2% either way is "about normal"."""
    pct = round(abs(point) * 100)
    if pct <= 2:
        return "About normal"
    return f"{pct}% {'below' if point < 0 else 'above'} normal"


def grass_card(answer: dict, season: dict) -> dict:
    g = answer["grass"]
    when = f"forecast as of {answer['as_of_words']}" if g.get("forecast") else "the season as measured"
    return {"label": f"Grass this season, {answer['season']}", "headline": grass_words(g["point"]),
            "detail": (f"{answer['county']} County, NE grassland: about {g['lb']:,.0f} lb an acre this season against a "
                       f"normal {g['normal_lb']:,.0f} ({when}). 8 in 10: {g['lb_low']:,.0f} to {g['lb_high']:,.0f}."),
            "value": g["point"], "low": g["low"], "high": g["high"], "unit": "share vs normal",
            "as_of": season["as_of"], "season": answer["season"], "source": GRASS_SOURCE, "method": GRASS_METHOD}


# --- the weeks file -----------------------------------------------------------------------------


def load_weeks() -> list[dict]:
    return json.loads(WEEKS.read_text(encoding="utf-8"))["weeks"] if WEEKS.exists() else []


def save_weeks(weeks: list[dict]) -> None:
    WEEKS.write_text(json.dumps({"format": 1, "weeks": weeks[:KEEP_WEEKS]}, indent=1) + "\n", encoding="utf-8")


def static_card(app_id: str, fips: str) -> dict | None:
    data = load_static(app_id)
    card = data["cards"].get(fips)
    if card is None:
        return None
    return {"label": card["label"], "headline": card["headline"], "detail": card["detail"],
            "value": card["value"], "low": card["low"], "unit": card["unit"],
            "source": data["source"], "method": data["method"]}


def herd_card(body: dict) -> dict:
    card = {k: body[k] for k in ("label", "headline", "detail", "value", "low", "high", "unit", "as_of",
                                 "market", "source")}
    card["market_slug"] = body.get("market_slug")  # links the tile to that barn's page
    return card


# --- the sale barns' weekly price sheets ------------------------------------------------------------

KEEP_BARN_WEEKS = 104  # two years per barn; the pages chart the last 12


def load_barns() -> dict:
    if BARNS_FILE.exists():
        return json.loads(BARNS_FILE.read_text(encoding="utf-8"))
    return {"format": 1, "barns": {}}


def record_barns(body: dict, today: date) -> str:
    """Add this week's sheet for every barn in Herd Planner's answer. A barn keeps its history even
    in weeks it doesn't sell; a re-run in the same week replaces that week."""
    data = load_barns()
    data["source"], data["method"] = body["source"], body["method"]
    for b in body["barns"]:
        entry = data["barns"].setdefault(str(b["slug"]), {"weeks": []})
        entry.update({k: b[k] for k in ("name", "city", "state", "sale", "is_hub")})
        if b.get("lat") is not None and b.get("lon") is not None:  # Herd Planner v0.41+: the barn's town on the map
            entry["lat"], entry["lon"] = b["lat"], b["lon"]
        week = {"week": week_id(today), "date": today.isoformat(), "last_sale": b["last_sale"],
                "fresh": b["fresh"], "prices": b["prices"]}
        entry["weeks"] = ([week] + [w for w in entry["weeks"] if w["week"] != week["week"]])[:KEEP_BARN_WEEKS]
        if b.get("seasons"):  # best months to sell (Herd Planner v0.21+): only the latest is kept
            entry["seasons"], entry["seasons_date"] = b["seasons"], today.isoformat()
    BARNS_FILE.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    return f"{len(body['barns'])} barns"


# --- which barn a county's steer tile names (October 2026) ---------------------------------------
# Scott: tell a rancher whose barn has no fresh price that it has none, and offer the nearest barns that do,
# rather than quietly showing another barn's price. Without a chosen barn, the tile names the nearest barn
# with a fresh price. Distances are straight-line miles from the middle of the county (county_centers.csv,
# the same centres as Herd Planner's) to the barn's town (from Herd Planner's /suite/barns), the same
# rule Herd Planner's own feed uses since v0.41.0.

CENTERS_FILE = ROOT / "content" / "county_centers.csv"
NEAR_MILES = 250  # past this a barn isn't "nearby": Oklahoma City, the benchmark, is the honest answer
NEARBY_SHOWN = 2  # the other fresh barns a tile lists
STEER_LB = 550


def county_centers() -> dict[str, tuple[float, float]]:
    rows = CENTERS_FILE.read_text(encoding="utf-8").splitlines()[1:]
    return {f: (float(lat), float(lon)) for f, lat, lon in (r.split(",") for r in rows if r)}


def miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle (straight-line) miles between two (latitude, longitude) points: the haversine formula."""
    from math import asin, cos, radians, sin, sqrt
    lat1, lat2 = radians(a[0]), radians(b[0])
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin(radians(b[1] - a[1]) / 2) ** 2
    return 2 * 3958.8 * asin(sqrt(h))


def barns_now(today: date | None = None, data: dict | None = None) -> dict[str, dict]:
    """Every barn's latest 550 lb steer price, as of `today`: {slug: {name, city, state, is_hub, lat, lon,
    last_sale, fresh, value, low, high}}. A barn whose latest sheet has no 550 lb steer is left out."""
    today = today or datetime.now(timezone.utc).date()
    out = {}
    for slug, b in (data or load_barns())["barns"].items():
        if not b.get("weeks"):
            continue
        week = b["weeks"][0]
        steer = next((p for p in week["prices"] if p["animal_class"] == "Steers" and p["weight_lb"] == STEER_LB), None)
        if not steer:
            continue
        sold = date.fromisoformat(week["last_sale"])
        out[slug] = {"slug": slug, "name": b["name"], "city": b["city"], "state": b["state"],
                     "is_hub": bool(b.get("is_hub")), "lat": b.get("lat"), "lon": b.get("lon"),
                     "last_sale": week["last_sale"], "fresh": (today - sold).days <= FRESH_DAYS,
                     "value": steer["price"], "low": steer["low"], "high": steer["high"]}
    return out


def nearby(fips: str, barns: dict[str, dict], centers: dict | None = None) -> list[list]:
    """[[slug, miles], ...] for every barn within NEAR_MILES of the county's middle, nearest first. Empty
    when the county or the barns' positions aren't known (an older Herd Planner sent no positions)."""
    here = (centers or county_centers()).get(fips)
    if not here:
        return []
    near = [[slug, round(miles(here, (b["lat"], b["lon"])))] for slug, b in barns.items()
            if b.get("lat") is not None and miles(here, (b["lat"], b["lon"])) <= NEAR_MILES]
    return sorted(near, key=lambda x: (x[1], x[0]))


def hub_of(barns: dict[str, dict]) -> str | None:
    return next((slug for slug, b in barns.items() if b["is_hub"]), None)


def choose(near: list[list], barns: dict[str, dict], chosen: str | None = None) -> dict:
    """Which steer tile a county gets. panel.js makes the same choice in the browser (keep the two alike).

    * a chosen barn is never swapped: fresh, its price ("barn"); not, "quiet" with the nearest fresh barns
      (up to NEARBY_SHOWN), or the benchmark when none has sold;
    * no barn chosen: the nearest barn with a fresh price ("barn"), else Oklahoma City as the benchmark."""
    hub = hub_of(barns)
    fresh = [slug for slug, _m in near if barns[slug]["fresh"]]
    if chosen in barns:
        if barns[chosen]["fresh"]:
            return {"kind": "barn", "barn": chosen}
        rows = [s for s in fresh if s != chosen][:NEARBY_SHOWN]
        bench = hub if not rows and hub and hub != chosen and barns[hub]["fresh"] else None
        return {"kind": "quiet", "barn": chosen, "rows": rows, "benchmark": bench}
    if fresh:
        return {"kind": "barn", "barn": fresh[0]}
    if hub and barns[hub]["fresh"]:
        return {"kind": "benchmark", "barn": hub}
    return {"kind": "none"}


def refresh(today: date | None = None, fetch=fetch_herd, barns=None, grass=None) -> tuple[dict, list[str]]:
    """Record this week (replacing it if refresh already ran this week). Returns (week, notes)."""
    today = today or datetime.now(timezone.utc).date()
    notes = copy_from_siblings()
    place = place_for(today)
    cards = {app: static_card(app, place["fips"]) for app in STATIC_APPS}
    # The steer price for every state the county picker offers (the nearest barn differs by state).
    # The week's own county comes first, so Herd Planner is already awake for the others.
    herd_by_state = {}
    for state in [place["state"]] + [s for s in STATE_NAMES if s != place["state"]]:
        body, note = fetch(state)
        notes.append(f"{HERD} ({state}): {note}")
        herd_by_state[state] = herd_card(body) if body else None
    cards[HERD] = herd_by_state[place["state"]]
    card, note = (grass or fetch_grass)(place["fips"])
    notes.append(f"{GRAZE}: {note}")
    cards[GRAZE] = card
    body, note = (barns or fetch_barns)()  # Herd Planner is awake by now
    notes.append(f"barn pages: {record_barns(body, today) if body else note}")
    week = {"week": week_id(today), "date": today.isoformat(), "place": place, "cards": cards,
            "herd_by_state": herd_by_state}
    weeks = [w for w in load_weeks() if w["week"] != week["week"]]
    save_weeks([week] + weeks)
    return week, notes


# --- what the site shows ------------------------------------------------------------------------


def current(today: date | None = None) -> dict:
    """The week to show: the latest recorded one, or (before the first refresh) today's place with
    the county cards and no steer price. A steer price older than FRESH_DAYS is dropped."""
    today = today or datetime.now(timezone.utc).date()
    weeks = load_weeks()
    if weeks:
        week = json.loads(json.dumps(weeks[0]))  # a copy
    else:
        place = place_for(today)
        week = {"week": week_id(today), "date": today.isoformat(), "place": place,
                "cards": {**{a: static_card(a, place["fips"]) for a in STATIC_APPS}, HERD: None}}
    stale = lambda c: c and (today - date.fromisoformat(c["as_of"])).days > FRESH_DAYS
    if stale(week["cards"].get(HERD)):
        week["cards"][HERD] = None
    by_state = week.get("herd_by_state") or {week["place"]["state"]: week["cards"].get(HERD)}
    week["herd_by_state"] = {st: (None if stale(c) else c) for st, c in by_state.items()}
    return week


# --- every county the picker offers ------------------------------------------------------------


def county_name(fips: str) -> str:
    """ "Hall County" from whichever county file has the county (their detail lines start with it)."""
    for app in STATIC_APPS:
        card = load_static(app)["cards"].get(fips)
        if card:
            return card["detail"].split(",")[0]
    return f"County {fips}"


def all_counties() -> list[dict]:
    """Every county either county app covers, sorted by state then name: the picker's list."""
    fips = set(load_static(CORN)["cards"]) | set(load_static(EQUIP)["cards"])
    rows = [{"fips": f, "state": STATE_OF_FIPS[f[:2]], "name": county_name(f)} for f in fips if f[:2] in STATE_OF_FIPS]
    return sorted(rows, key=lambda r: (r["state"], r["name"]))


def main(argv: list[str]) -> int:
    if argv[:1] != ["refresh"]:
        print(__doc__.split("\n\n")[1])
        return 2
    week, notes = refresh()
    p = week["place"]
    print(f"{week['week']}: {p['county']}, {p['state_name']}")
    for line in notes:
        print("  " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
