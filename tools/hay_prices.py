"""Refresh the hay chart's numbers in Why We Built This (content/hay_prices.json) from the Grazing Planner.

    python tools/hay_prices.py

Reads ..\\grazing-planner\\data\\app\\hay.json (the Grazing Planner builds it from USDA's Nebraska Direct Hay Report,
scripts/build_hay.py) and keeps, for each month, the price the Planner showed at that month's last report: grass hay
and fair-to-good alfalfa, $ a ton, from the trades of the 8 weeks before, weighted by tons. Months missing either kind
are left out. Then run python build.py. Scott chose the chart's place (A of notes/hay-chart-*-2026-10-24.png).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "grazing-planner" / "data" / "app" / "hay.json"
OUT = ROOT / "content" / "hay_prices.json"


def monthly(hay: dict) -> dict:
    last = {}
    for week in sorted(hay["weeks"]):
        last[week[:7]] = week                      # the month's last report week wins
    months, grass, alfalfa = [], [], []
    for month, week in sorted(last.items()):
        w = hay["weeks"][week]
        if w.get("grass") and w.get("alfalfa"):
            months.append(month)
            grass.append(round(w["grass"]["price"]))
            alfalfa.append(round(w["alfalfa"]["price"]))
    return {"_about": "Made by tools/hay_prices.py from the Grazing Planner's data/app/hay.json; don't edit by hand.",
            "window_weeks": hay["window_weeks"], "source": hay["source"], "months": months, "grass": grass,
            "alfalfa": alfalfa}


def main() -> int:
    if not SOURCE.exists():
        print(f"Not found: {SOURCE}. Build it in the Grazing Planner first (scripts/build_hay.py).")
        return 2
    data = monthly(json.loads(SOURCE.read_text(encoding="utf-8")))
    OUT.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    print(f"{len(data['months'])} months, {data['months'][0]} to {data['months'][-1]}: grass hay ${data['grass'][-1]}, "
          f"alfalfa ${data['alfalfa'][-1]} a ton. Wrote {OUT.name}; now run python build.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
