"""The live panel: red marks the downside, never alone, and the rounded numbers agree."""

import re
from pathlib import Path

import hero

ROOT = Path(__file__).resolve().parents[1]

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
    # Option A (2026-10-08): the button follows the county's name, in the same row, so it sits on what it changes.
    name = html[html.index('<div class="live-name">'):]
    assert name.index("<h2>") < name.index('class="live-pick-open"') < name.index("</div>")
    assert '<form class="live-pick" id="live-pick" hidden>' in html
    assert 'src="panel.js"' in html
    for slot in ("herd", "calves", "corn", "days"):
        assert f'data-tile="{slot}"' in html


def build_panel():
    return hero.panel(WEEK, [SEASON], lambda iso: iso)


# --- the pins on the home page's photo ("numbers on the land") ---------------------------------

GRASS = {"label": "Grass this season, 2026", "headline": "8% below normal", "value": -0.081, "low": -0.144,
         "high": -0.0267, "season": 2026}
HERD = {"value": 462.52, "low": 442.39, "high": 487.0, "as_of": "2026-09-16", "market_slug": "bassett-ne-1852",
        "market": "Bassett Livestock Auction, Bassett NE"}


def week_with(**cards):
    return {**WEEK, "cards": {**WEEK["cards"], **cards}}


def test_the_pins_are_three_named_slots_the_county_picker_can_swap():
    html = hero.pins(WEEK)
    assert re.findall(r'data-pin="(\w+)"', html) == ["herd", "land", "corn"]
    assert 'id="pins"' in html and '<span class="pins-where">Frontier County, Nebraska</span>' in html


def test_the_pins_show_the_same_numbers_as_the_panel_below_them():
    week = week_with(**{"herd-planner": HERD})
    pins, panel = hero.pins(week), hero.panel(week, [SEASON], lambda iso: iso)
    assert "$463<small>/cwt</small>" in pins and "$463/cwt" in panel
    assert "8 in 10 sales $442 to $487" in pins and "Bassett NE" in pins
    assert "146<small> bu/acre</small>" in pins and "146 bu/acre" in panel
    assert "128 in a bad year" in pins and "below 128 bu/acre" in panel
    assert "55<small> of 61 days</small>" in pins and "48 in a wet fall" in pins   # round(48.5) as the panel rounds it
    assert "workable even in a wet fall (48)" in panel


def test_the_steer_pin_links_to_the_barn_its_price_came_from():
    html = hero.pins(week_with(**{"herd-planner": HERD}), lambda slug: f"barn-{slug}.html")
    assert 'href="barn-bassett-ne-1852.html" data-pin="herd"' in html


def test_a_pin_with_no_price_says_so_instead_of_showing_an_old_one():
    html = hero.pins(WEEK)
    assert "No fresh price" in html and 'class="pin quiet"' in html and "$" not in html


def test_the_middle_pin_is_grass_when_the_week_has_it_and_field_days_when_not():
    grass = hero.pins(week_with(**{"grazing-planner": GRASS}))
    assert "Grass this season" in grass and "Fall field days" not in grass
    assert 'href="grazing-planner.html" data-pin="land"' in grass
    days = hero.pins(week_with(**{"grazing-planner": None}))
    assert "Fall field days" in days and "Grass this season" not in days


def test_red_on_a_pin_always_comes_with_an_arrow_and_words():
    short = hero.grass_pin(GRASS, "Frontier County")
    assert '<span class="down" aria-hidden="true">▼</span> 8%<small> below normal</small>' in short
    good = hero.grass_pin({**GRASS, "value": 0.12}, "Frontier County")
    assert 'class="down"' not in good and "12%<small> above normal</small>" in good
    assert "About normal" in hero.grass_pin({**GRASS, "value": -0.01}, "Frontier County")


def test_picker_data_carries_every_countys_pins(tmp_path, monkeypatch):
    import json

    import build
    import cards

    monkeypatch.setattr(build, "OUT", tmp_path / "docs")
    site = build.build()
    data = json.loads((site / "panel-data.json").read_text(encoding="utf-8"))
    assert data["format"] == 3 and set(data["herd_pin"]) == set(cards.STATE_NAMES)   # by state: the fallback
    assert all(pin.startswith('<a class="pin') and 'data-pin="herd"' in pin for pin in data["herd_pin"].values())
    for county in data["counties"].values():
        assert 'data-pin="land"' in county["pins"]["land"] and 'data-pin="corn"' in county["pins"]["corn"]
    # A picked county's pins carry that county's own numbers, the same ones as its tiles.
    hall = data["counties"]["31079"]
    bushels = re.search(r"(\d+) bu/acre", hall["corn"]).group(1)
    assert f"{bushels}<small> bu/acre</small>" in hall["pins"]["corn"]
    page = (site / "index.html").read_text(encoding="utf-8")
    script = (site / "panel.js").read_text(encoding="utf-8")
    assert 'id="pins"' in page and 'getElementById("pins")' in script and "data.herd_pin" in script


# --- the steer price names the day of its sale (October 7, 2026) ------------------------------------------------
# Scott, of the home page's panel: the field-days tile carries real dates ("Oct 1 to Nov 30") and the steer tile
# said "this week". The price is the nearest barn's latest sale in the last three weeks, so it can be two weeks
# old; the label now says which sale.

FRESH = {"label": "550 lb steer, this week", "headline": "$456/cwt", "value": 456.36, "low": 436.5, "high": 480.33,
         "detail": "About $2,510 a head at Bassett Livestock Auction, Bassett NE (sale of Sep 16). 8 in 10 sales land between $437 and $480/cwt.",
         "unit": "$/cwt", "as_of": "2026-09-16", "market": "Bassett Livestock Auction, Bassett NE",
         "source": "USDA AMS MyMarketNews auction reports", "market_slug": 1852}


def test_the_steer_label_names_the_sale_and_not_this_week():
    assert hero.steer_label(FRESH) == "550 lb steer, sale of Sep 16"
    assert hero.steer_label({**FRESH, "as_of": "2026-10-02"}) == "550 lb steer, sale of Oct 2"     # no leading zero
    tile = hero.herd_tile(FRESH, "Nebraska")
    label = re.search(r'<span class="live-label">(.*?)</span>', tile).group(1)
    note = re.search(r'<span class="live-note">(.*?)</span>', tile).group(1)
    assert label == "550 lb steer, sale of Sep 16" and "this week" not in tile
    assert note == "About $2,510 a head at Bassett Livestock Auction, Bassett NE."      # the day is said once, in the label
    pin = hero.herd_pin(FRESH, "Nebraska")
    assert '<span class="pin-label">550 lb steer, sale of Sep 16</span>' in pin and "this week" not in pin


def test_with_no_fresh_price_there_is_no_sale_to_name():
    assert hero.steer_label(None) == "550 lb steer, this week"
    for html in (hero.herd_tile(None, "Nebraska"), hero.herd_pin(None, "Nebraska")):
        assert "550 lb steer, this week" in html and "No fresh price" in html and "sale of" not in html


def test_the_app_pages_card_names_the_sale_too():
    """The saved card keeps Herd Planner's own label ("this week"); the page shows the sale's day, which stays
    true when the same card is shown again under Recent Weeks. Other apps' cards keep their own labels."""
    import build

    herd = build.stat_card({"id": "herd-planner", "name": "Herd Planner"}, FRESH, WEEK)
    assert '<span class="stat-label">550 lb steer, sale of Sep 16</span>' in herd and "this week" not in herd
    corn = build.stat_card({"id": "corn-yield-predictor", "name": "Yield Predictor"},
                           {**WEEK["cards"]["corn-yield-predictor"], "detail": "d", "source": "s"}, WEEK)
    assert '<span class="stat-label">Trend corn yield, 2026</span>' in corn
    none = build.stat_card({"id": "herd-planner", "name": "Herd Planner"}, None, WEEK)
    assert '<span class="stat-label">550 lb steer, this week</span>' in none and "No fresh sale-barn price" in none


def test_the_change_button_has_a_drawn_pin_and_a_full_name_for_screen_readers():
    """Scott, 2026-10-08: the button could look better. The emoji pin drew differently on every phone; it is now a
    drawn pin, and once a county is picked the button says "Change" (heard as "Change county")."""
    css = (ROOT / "static" / "site.css").read_text(encoding="utf-8")
    js = (ROOT / "static" / "panel.js").read_text(encoding="utf-8")
    assert "\\1F4CD" not in css and "mask: url(" in css and ".live-name {" in css
    assert 'openButton.textContent = yours ? "Change" : "See your county"' in js
    assert 'setAttribute("aria-label", "Change county")' in js and '"Change county"; openForm' not in js
