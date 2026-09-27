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
HERD, CORN, EQUIP = "herd-planner", "corn-yield-predictor", "farm-equipment-planner"
STATIC_APPS = (CORN, EQUIP)
SIBLINGS = {  # where each app's exported card file lives, next to this project
    CORN: ROOT.parent / "crop-yield-predictor" / "data" / "processed" / "suite_card.json",
    EQUIP: ROOT.parent / "farm-equipment-planner" / "regional" / "data" / "suite_card.json",
}
HERD_PLANNER_URL = os.getenv("HERD_PLANNER_URL", "https://herd-planner.onrender.com")
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


def _get(url: str) -> tuple[int, dict]:
    """One HTTP GET returning (status, JSON). Tests replace this."""
    req = urllib.request.Request(url, headers={"User-Agent": "company-site weekly cards"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        return err.code, {}


def fetch_herd(state: str, wait=time.sleep) -> tuple[dict | None, str]:
    """(card, note). Tries while Render wakes the app; never returns sample prices."""
    url = f"{HERD_PLANNER_URL.rstrip('/')}/suite/summary?" + urllib.parse.urlencode({"state": state})
    last = ""
    for attempt in range(WAKE_TRIES):
        try:
            status, body = _get(url)
        except (OSError, ValueError) as err:  # timeouts, refused connections, a half-awake server
            status, body, last = 0, {}, f"no answer ({err.__class__.__name__})"
        if status == 200:
            if body.get("is_sample"):
                return None, "Herd Planner only has sample prices; not published"
            return body, "ok"
        if status:
            last = f"HTTP {status}"
            if status in (404, 409, 422):  # a real answer: waiting won't change it
                break
        if attempt + 1 < WAKE_TRIES:
            wait(WAKE_WAIT)
    return None, f"Herd Planner didn't give a price: {last}"


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
    return {k: body[k] for k in ("label", "headline", "detail", "value", "low", "high", "unit", "as_of",
                                 "market", "source")}


def refresh(today: date | None = None, fetch=fetch_herd) -> tuple[dict, list[str]]:
    """Record this week (replacing it if refresh already ran this week). Returns (week, notes)."""
    today = today or datetime.now(timezone.utc).date()
    notes = copy_from_siblings()
    place = place_for(today)
    cards = {app: static_card(app, place["fips"]) for app in STATIC_APPS}
    body, note = fetch(place["state"])
    notes.append(f"{HERD}: {note}")
    cards[HERD] = herd_card(body) if body else None
    week = {"week": week_id(today), "date": today.isoformat(), "place": place, "cards": cards}
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
    herd = week["cards"].get(HERD)
    if herd and (today - date.fromisoformat(herd["as_of"])).days > FRESH_DAYS:
        week["cards"][HERD] = None
    return week


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
