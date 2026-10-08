"""The steer tile by barn (October 2026). Scott's rule, option A of the 2026-10-07 mockups: a county's tile names
the nearest barn with a fresh price; a barn the rancher chose is never swapped for another, and when it hasn't sold in
three weeks the tile says so and lists the nearest barns that have."""

import json
import re
from datetime import date
from pathlib import Path

import pytest

import cards
import hero

ROOT = Path(__file__).resolve().parents[1]
HP_CENTERS = ROOT.parent / "herd-planner" / "src" / "herd_planner" / "market" / "county_centers.csv"
LINCOLN, ROCK, SCOTT_IA = "31111", "31149", "19163"   # North Platte's county, Bassett's, Davenport's
DAY = date(2026, 10, 9)
POS = {"1280": (35.468, -97.516), "1851": (41.782, -99.133), "1852": (42.586, -99.538), "3653": (41.124, -100.765)}
TOWN = {"1280": ("Oklahoma National Stockyards", "Oklahoma City", "OK"), "1851": ("Burwell Livestock Market", "Burwell", "NE"),
        "1852": ("Bassett Livestock Auction", "Bassett", "NE"), "3653": ("North Platte Stockyards", "North Platte", "NE")}


def barns_file(sold: dict, positions=True) -> dict:
    """A barns.json as the Friday job writes it: {slug: last sale}, each with one week's price sheet."""
    out = {"format": 1, "barns": {}}
    for i, (slug, last) in enumerate(sold.items()):
        name, city, state = TOWN[slug]
        price = 400.0 + 10 * i
        entry = {"name": name, "city": city, "state": state, "sale": "Feeder Cattle Auction", "is_hub": slug == "1280",
                 "weeks": [{"week": "2026-W41", "date": "2026-10-09", "last_sale": last, "fresh": True,
                            "prices": [{"animal_class": "Steers", "weight_lb": 550, "price": price, "low": price - 20, "high": price + 20},
                                       {"animal_class": "Heifers", "weight_lb": 550, "price": price - 40, "low": price - 60, "high": price - 20}]}]}
        if positions:
            entry["lat"], entry["lon"] = POS[slug]
        out["barns"][slug] = entry
    return out


SOLD = {"1280": "2026-10-05", "1851": "2026-10-02", "1852": "2026-09-16", "3653": "2026-09-29"}   # Bassett 23 days ago


@pytest.fixture
def barns():
    return cards.barns_now(DAY, barns_file(SOLD))


# --- the rule ------------------------------------------------------------------------------------


def test_fresh_means_a_sale_in_the_last_three_weeks_by_the_day_asked(barns):
    assert barns["1851"]["fresh"] and not barns["1852"]["fresh"]
    assert cards.barns_now(date(2026, 10, 7), barns_file(SOLD))["1852"]["fresh"]       # 21 days: still fresh
    assert barns["1851"]["value"] == 410.0 and barns["1851"]["low"] == 390.0          # the 550 lb steer, not heifers


def test_nearby_is_by_straight_line_miles_from_the_middle_of_the_county(barns):
    near = cards.nearby(LINCOLN, barns)
    assert [s for s, _ in near] == ["3653", "1851", "1852"] and near[0][1] <= 10        # Oklahoma City is over 250 miles
    assert [s for s, _ in cards.nearby(ROCK, barns)][:2] == ["1852", "1851"]
    assert cards.nearby(SCOTT_IA, barns) == []                                        # eastern Iowa: nothing within 250
    assert cards.nearby("99999", barns) == []


def test_without_a_chosen_barn_the_nearest_fresh_barn_is_named(barns):
    assert cards.choose(cards.nearby(LINCOLN, barns), barns) == {"kind": "barn", "barn": "3653"}
    # Rock County: Bassett is nearest but resting, so Burwell.
    assert cards.choose(cards.nearby(ROCK, barns), barns) == {"kind": "barn", "barn": "1851"}


def test_a_chosen_barn_is_never_swapped(barns):
    assert cards.choose(cards.nearby(ROCK, barns), barns, chosen="3653") == {"kind": "barn", "barn": "3653"}
    quiet = cards.choose(cards.nearby(ROCK, barns), barns, chosen="1852")
    assert quiet == {"kind": "quiet", "barn": "1852", "rows": ["1851", "3653"], "benchmark": None}


def test_with_nothing_fresh_nearby_oklahoma_city_is_the_benchmark(barns):
    assert cards.choose(cards.nearby(SCOTT_IA, barns), barns) == {"kind": "benchmark", "barn": "1280"}
    only_bassett = {s: b for s, b in barns.items() if s in ("1852", "1280")}
    named = cards.choose(cards.nearby(ROCK, only_bassett), only_bassett, chosen="1852")
    assert named == {"kind": "quiet", "barn": "1852", "rows": [], "benchmark": "1280"}
    stale_hub = {**only_bassett, "1280": {**only_bassett["1280"], "fresh": False}}
    assert cards.choose([], stale_hub) == {"kind": "none"}


# --- what the tiles say ----------------------------------------------------------------------------


def test_the_tile_is_a_box_so_its_links_never_sit_inside_a_link(barns):
    tile, _ = hero.steer_for(cards.choose(cards.nearby(ROCK, barns), barns, chosen="1852"), barns)
    assert tile.lstrip().startswith('<div class="live-tile quiet" data-tile="herd">')
    assert tile.count("<a ") == tile.count("</a>") == 4          # the headline, two barns, Change barn
    assert 'class="live-main"' in tile and "data-change-barn hidden" in tile


def test_a_resting_chosen_barn_says_so_and_lists_the_nearest_that_sold(barns):
    tile, pin = hero.steer_for(cards.choose(cards.nearby(ROCK, barns), barns, chosen="1852"), barns)
    text = re.sub(r"<[^>]+>", " ", tile)
    assert "550 lb steer at Bassett" in text and "No fresh price" in text and "Bassett last sold Sep 16." in text
    assert "Fresh nearby, $/cwt" in text
    assert text.index("Burwell") < text.index("North Platte")                       # nearest first
    assert "$410" in text and "Oct 2" in text and "$430" in text and "Sep 29" in text
    assert "No fresh price" in pin and "Last sale Sep 16" in pin and 'class="pin quiet"' in pin


def test_the_benchmark_says_why_it_is_shown(barns):
    tile, pin = hero.steer_for(cards.choose([], barns), barns)
    assert "the national benchmark: no barn within 250 miles has sold in three weeks" in tile
    assert "Oklahoma City OK" in pin and "national benchmark" in pin
    only = {s: b for s, b in barns.items() if s in ("1852", "1280")}
    tile, _ = hero.steer_for(cards.choose(cards.nearby(ROCK, only), only, chosen="1852"), only)
    assert "Nothing fresh nearby. The national benchmark, $/cwt:" in tile and "Oklahoma City" in tile


def test_a_fresh_barn_tile_names_its_sale_and_its_town(barns):
    tile, pin = hero.steer_for({"kind": "barn", "barn": "3653"}, barns, lambda slug: f"barn-{slug}.html")
    assert "550 lb steer, sale of Sep 29" in tile and "$430/cwt" in tile and "About $2,365 a head at North Platte, NE." in tile
    assert 'href="barn-3653.html"' in tile and 'href="barn-3653.html" data-pin="herd"' in pin


# --- the Friday job and the build ------------------------------------------------------------------


def test_the_friday_job_keeps_each_barns_position(tmp_path, monkeypatch):
    monkeypatch.setattr(cards, "BARNS_FILE", tmp_path / "barns.json")
    sheet = {"slug": 3653, "name": "North Platte Stockyards", "city": "North Platte", "state": "NE", "sale": "Feeder Cattle Auction",
             "last_sale": "2026-10-05", "fresh": True, "is_hub": False, "lat": 41.124, "lon": -100.765,
             "prices": [{"animal_class": "Steers", "weight_lb": 550, "price": 430.0, "low": 410.0, "high": 450.0}]}
    cards.record_barns({"source": "s", "method": "m", "barns": [sheet]}, DAY)
    saved = json.loads((tmp_path / "barns.json").read_text(encoding="utf-8"))["barns"]["3653"]
    assert (saved["lat"], saved["lon"]) == (41.124, -100.765)
    # An older Herd Planner sends no position: the one already saved stays.
    cards.record_barns({"source": "s", "method": "m", "barns": [{k: v for k, v in sheet.items() if k not in ("lat", "lon")}]}, DAY)
    saved = json.loads((tmp_path / "barns.json").read_text(encoding="utf-8"))["barns"]["3653"]
    assert (saved["lat"], saved["lon"]) == (41.124, -100.765)


def test_the_build_names_the_nearest_fresh_barn_and_ships_the_pieces(tmp_path, monkeypatch):
    import build

    monkeypatch.setattr(build, "OUT", tmp_path / "docs")
    real = cards.load_barns
    monkeypatch.setattr(cards, "load_barns", lambda: barns_file(SOLD))
    real_now = cards.barns_now
    monkeypatch.setattr(cards, "barns_now", lambda today=None, data=None: real_now(DAY, data))
    site = build.build()
    data = json.loads((site / "panel-data.json").read_text(encoding="utf-8"))
    assert data["format"] == 3 and data["hub"] == "1280" and data["fresh_days"] == cards.FRESH_DAYS
    assert set(data["barns"]) == set(SOLD) and data["near_token"] in data["barns"]["1852"]["quiet"]
    assert "bench_tile" in data["barns"]["1280"] and "bench_tile" not in data["barns"]["3653"]
    assert [s for s, _ in data["counties"][LINCOLN]["barns"]][:1] == ["3653"]
    assert data["counties"][SCOTT_IA]["barns"] == []
    page = (site / "index.html").read_text(encoding="utf-8")
    week = cards.current()
    expect = cards.choose(cards.nearby(week["place"]["fips"], cards.barns_now()), cards.barns_now())
    city = TOWN[expect["barn"]][1] if expect.get("barn") else None
    tile = page[page.index('data-tile="herd"') - 40:page.index('data-tile="calves"')]
    assert city and city in tile
    assert '<label>Sale barn <select name="barn"></select></label>' in page
    script = (site / "panel.js").read_text(encoding="utf-8")
    assert "panel-barn" in script and "data.near_token" in script
    monkeypatch.setattr(cards, "load_barns", real)


def test_without_barn_positions_the_tile_falls_back_to_the_state(tmp_path, monkeypatch):
    import build

    monkeypatch.setattr(build, "OUT", tmp_path / "docs")
    monkeypatch.setattr(cards, "load_barns", lambda: barns_file(SOLD, positions=False))
    site = build.build()
    data = json.loads((site / "panel-data.json").read_text(encoding="utf-8"))
    assert "barns" not in data and set(data["herd"]) == set(cards.STATE_NAMES)
    assert all("barns" not in c for c in data["counties"].values())


# --- the county centres ------------------------------------------------------------------------------


def test_every_county_the_picker_offers_has_a_centre():
    centers = cards.county_centers()
    assert {c["fips"] for c in cards.all_counties()} <= set(centers)
    assert all(40.0 < lat < 43.6 and -104.1 < lon < -95.3 for f, (lat, lon) in centers.items() if f.startswith("31"))


@pytest.mark.skipif(not HP_CENTERS.exists(), reason="Herd Planner v0.41+ isn't checked out next to this project")
def test_the_county_centres_match_herd_planners():
    """The site and Herd Planner must measure from the same points, or they'd name different barns."""
    master = {r.split(",")[0]: r for r in HP_CENTERS.read_text(encoding="utf-8").splitlines()[1:]}
    ours = cards.CENTERS_FILE.read_text(encoding="utf-8").splitlines()[1:]
    assert ours and all(master.get(r.split(",")[0]) == r for r in ours)


def test_the_privacy_page_names_the_barn_kept_in_the_browser(tmp_path, monkeypatch):
    import build

    monkeypatch.setattr(build, "OUT", tmp_path / "docs")
    page = (build.build() / "privacy.html").read_text(encoding="utf-8")
    assert "the county and sale barn you pick on the home page" in page
