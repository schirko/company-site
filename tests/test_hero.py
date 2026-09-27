"""The live panel: red marks the downside, never alone, and the rounded numbers agree."""

import re

import hero

WEEK = {"week": "2026-W39", "date": "2026-09-25",
        "place": {"fips": "31063", "state": "NE", "county": "Frontier County", "state_name": "Nebraska"},
        "cards": {"herd-planner": None,
                  "corn-yield-predictor": {"label": "Trend corn yield, 2026", "headline": "146 bu/acre",
                                           "value": 146.4, "low": 128.2},
                  "farm-equipment-planner": {"label": "Fall field days, Oct 1 to Nov 30", "headline": "55 of 61 days",
                                             "value": 55.0, "low": 48.5}}}
SEASON = {"chart": "seasonal", "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
          "series": [{"name": "calves", "index": [1.011, 1.025, 1.049, 1.033, 1.004, 1.022, 1.016, 1.015,
                                                  0.959, 0.940, 0.944, 0.980]}]}


def build():
    return hero.panel(WEEK, [SEASON], lambda iso: iso)


def test_field_day_numbers_add_up_to_61():
    html = build()
    wet = int(re.search(r"workable even in a wet fall \((\d+)\)", html).group(1))
    lost = int(re.search(r"(\d+) lost in a wet fall", html).group(1))
    assert wet + lost == 61
    dark = re.search(rf'<path d="([^"]*)" fill="{hero.BLUE}"', html).group(1)
    assert dark.count("z") == wet  # one dark square per workable wet-fall day


def test_red_always_comes_with_an_arrow_and_words():
    html = build()
    for flag in re.findall(r'<span class="badge down">(.*?)</span>\s', html):
        assert "▼" in flag
    assert "below trend" in html  # September calves run 4% under the trend


def test_missing_price_is_said_plainly():
    assert "No fresh price" in build()


# --- "See your county" ------------------------------------------------------------------------


def test_picker_data_covers_every_county_with_its_own_tiles(tmp_path, monkeypatch):
    import json

    import build
    import cards

    monkeypatch.setattr(build, "OUT", tmp_path / "docs")
    site = build.build()
    data = json.loads((site / "panel-data.json").read_text(encoding="utf-8"))
    counties = cards.all_counties()
    assert len(data["counties"]) == len(counties) >= 150
    assert data["default"] in data["counties"]
    assert set(data["herd"]) == set(cards.STATE_NAMES)
    hall = data["counties"]["31079"]
    assert hall["name"] == "Hall County" and 'data-tile="corn"' in hall["corn"] and 'data-tile="days"' in hall["days"]
    assert "Hall County, Nebraska" in hall["corn"]
    # A county only one app covers says so, instead of an empty tile.
    iowa_only = next(f for f, c in data["counties"].items() if c["state"] == "IA" and "Not covered yet" in c["days"])
    assert "Equipment Planner covers" in data["counties"][iowa_only]["days"]
    # Small enough to load on a phone: GitHub Pages compresses it to a few percent of this.
    assert (site / "panel-data.json").stat().st_size < 700_000


def test_picker_starts_hidden_so_the_page_works_without_javascript():
    html = build_panel()
    assert '<button type="button" class="live-pick-open" hidden' in html
    assert '<form class="live-pick" id="live-pick" hidden>' in html
    assert 'src="panel.js"' in html
    for slot in ("herd", "calves", "corn", "days"):
        assert f'data-tile="{slot}"' in html


def build_panel():
    return hero.panel(WEEK, [SEASON], lambda iso: iso)
