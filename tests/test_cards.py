"""The weekly stat cards: the place of the week, the refresh, and what the pages show."""

import json
from datetime import date

import pytest

import build
import cards

STEER = {"app": "herd-planner", "label": "550 lb steer, this week", "headline": "$395/cwt",
         "detail": "About $2,173 a head at Huss Livestock Market, Kearney NE (sale of Sep 23). "
                   "8 in 10 sales land between $370 and $420/cwt.",
         "value": 395.0, "low": 370.0, "high": 420.0, "unit": "$/cwt", "as_of": "2026-09-23",
         "market": "Huss Livestock Market, Kearney NE", "source": "USDA AMS MyMarketNews auction reports",
         "link": "https://herd-planner.onrender.com/", "is_sample": False}
FRIDAY = date(2026, 9, 25)


@pytest.fixture
def weeks_file(tmp_path, monkeypatch):
    """A scratch weeks.json, and no copying from sibling projects, so tests never touch the real files."""
    monkeypatch.setattr(cards, "WEEKS", tmp_path / "weeks.json")
    monkeypatch.setattr(cards, "copy_from_siblings", lambda: [])
    monkeypatch.setattr(cards, "fetch_barns", lambda: (None, "not asked in tests"))
    monkeypatch.setattr(cards, "BARNS_FILE", tmp_path / "barns.json")
    monkeypatch.setattr(build, "OUT", tmp_path / "docs")  # never leave test numbers in the real docs/
    return tmp_path / "weeks.json"


def got_price(state):
    return dict(STEER), "ok"


def no_price(state):
    return None, "Herd Planner didn't give a price: HTTP 404"


def test_every_week_has_a_place_with_all_county_numbers():
    order = cards.rotation()
    assert len(order) >= 50 and len(set(order)) == len(order)
    seen = {cards.place_for(date(2026, 1, 5) + (date(2026, 1, 12) - date(2026, 1, 5)) * i)["fips"]
            for i in range(len(order))}
    assert seen == set(order)  # every county comes around once before any repeats
    p = cards.place_for(FRIDAY)
    assert p["county"].endswith("County") and p["state"] in ("NE", "IA")
    assert cards.static_card(cards.CORN, p["fips"]) and cards.static_card(cards.EQUIP, p["fips"])


def test_the_place_stays_put_all_week():
    assert cards.place_for(date(2026, 9, 21)) == cards.place_for(date(2026, 9, 27))  # Monday to Sunday
    assert cards.place_for(date(2026, 9, 28)) != cards.place_for(date(2026, 9, 27))


def test_refresh_records_the_week_and_replaces_a_rerun(weeks_file):
    week, notes = cards.refresh(FRIDAY, fetch=got_price)
    assert week["week"] == "2026-W39" and week["cards"]["herd-planner"]["headline"] == "$395/cwt"
    assert "is_sample" not in week["cards"]["herd-planner"] and any(n.startswith("herd-planner (") and n.endswith("ok") for n in notes)
    cards.refresh(FRIDAY, fetch=no_price)  # run again the same week
    weeks = cards.load_weeks()
    assert len(weeks) == 1 and weeks[0]["cards"]["herd-planner"] is None
    cards.refresh(date(2026, 10, 2), fetch=got_price)
    assert [w["week"] for w in cards.load_weeks()] == ["2026-W40", "2026-W39"]


def test_old_steer_prices_are_not_shown_as_this_week(weeks_file):
    cards.refresh(FRIDAY, fetch=got_price)
    assert cards.current(FRIDAY)["cards"]["herd-planner"]
    assert cards.current(date(2026, 10, 30))["cards"]["herd-planner"] is None


def test_before_the_first_refresh_the_county_numbers_still_show(weeks_file):
    week = cards.current(FRIDAY)
    assert week["cards"]["herd-planner"] is None and week["cards"]["corn-yield-predictor"]


def test_sample_prices_are_never_published(monkeypatch):
    monkeypatch.setattr(cards, "_get", lambda url: (200, {**STEER, "is_sample": True}))
    card, note = cards.fetch_herd("NE", wait=lambda s: None)
    assert card is None and "sample" in note


def test_a_sleeping_herd_planner_is_waited_for(monkeypatch):
    answers = iter([TimeoutError("asleep"), TimeoutError("asleep"), (200, STEER)])

    def get(url):
        a = next(answers)
        if isinstance(a, Exception):
            raise a
        return a
    waits = []
    monkeypatch.setattr(cards, "_get", get)
    card, note = cards.fetch_herd("NE", wait=waits.append)
    assert card["headline"] == "$395/cwt" and len(waits) == 2


def test_a_missing_endpoint_is_not_waited_for(monkeypatch):
    calls = []
    monkeypatch.setattr(cards, "_get", lambda url: calls.append(url) or (404, {}))
    card, note = cards.fetch_herd("NE", wait=lambda s: None)
    assert card is None and "404" in note and len(calls) == 1
    assert calls[0].endswith("/suite/summary?state=NE")


def test_pages_show_the_week(weeks_file):
    cards.refresh(FRIDAY, fetch=got_price)
    site = build.build()
    week = cards.load_weeks()[0]
    home = (site / "index.html").read_text(encoding="utf-8")
    assert f'<span class="live-where">{week["place"]["county"]}' in home and "$395/cwt" in home
    herd = (site / "herd-planner.html").read_text(encoding="utf-8")
    assert "Huss Livestock Market" in herd and "$370 to $420" in herd
    corn = (site / "corn-yield-predictor.html").read_text(encoding="utf-8")
    assert week["cards"]["corn-yield-predictor"]["headline"] in corn
    assert "This week" in corn.split('name="description"')[1].split(">")[0]  # the number is in the search snippet


def test_a_week_without_a_price_says_so(weeks_file):
    cards.refresh(FRIDAY, fetch=no_price)
    home = (build.build() / "index.html").read_text(encoding="utf-8")
    assert "No fresh price" in home and "No sale barn near" in home


def test_sitemap_lists_every_page(weeks_file):
    site = build.build()
    xml = (site / "sitemap.xml").read_text(encoding="utf-8")
    for name in ("about.html", "methods.html", "herd-planner.html", "farm-equipment-planner.html"):
        assert name in xml
    assert "404.html" not in xml


def test_the_shipped_card_files_are_readable():
    for app_id in cards.STATIC_APPS:
        data = cards.load_static(app_id)
        assert data["format"] == 1 and data["cards"] and data["source"] and data["method"]
    if cards.WEEKS.exists():
        for w in cards.load_weeks():
            herd = w["cards"].get("herd-planner")
            assert herd is None or "sample" not in herd["source"].lower()
