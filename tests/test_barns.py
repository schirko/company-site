"""One page per sale barn: saved weekly from Herd Planner, one page each, an index, honest when stale."""

import json
from datetime import date, timedelta

import pytest

import barn_pages
import build
import cards


def sheet(price):
    rows = []
    for cls, off in (("Steers", 0), ("Heifers", -30)):
        for w in (400, 500, 550, 600, 700, 800):
            p = price + off - (w - 550) * 0.15
            rows.append({"animal_class": cls, "weight_lb": w, "price": p, "low": p * 0.94, "high": p * 1.05})
    return rows


def answer(price, fresh=True, last_sale="2026-09-23"):
    return {"as_of": "2026-09-25", "hub": 1280, "source": "USDA AMS MyMarketNews auction reports",
            "method": "Herd Planner's price model.",
            "barns": [{"slug": 1848, "name": "Huss Livestock Market", "city": "Kearney", "state": "NE",
                       "sale": "Feeder Cattle Auction", "last_sale": last_sale, "fresh": fresh, "is_hub": False,
                       "prices": sheet(price)},
                      {"slug": 1849, "name": "Lexington Livestock Market", "city": "Lexington", "state": "NE",
                       "sale": "Feeder Cattle Auction", "last_sale": last_sale, "fresh": fresh, "is_hub": False,
                       "prices": sheet(price - 5)}]}


@pytest.fixture
def barns_file(tmp_path, monkeypatch):
    monkeypatch.setattr(cards, "BARNS_FILE", tmp_path / "barns.json")
    monkeypatch.setattr(cards, "WEEKS", tmp_path / "weeks.json")
    monkeypatch.setattr(build, "OUT", tmp_path / "docs")
    return tmp_path / "barns.json"


def test_each_week_is_added_and_a_rerun_replaces_it(barns_file):
    friday = date(2026, 9, 25)
    cards.record_barns(answer(400), friday)
    cards.record_barns(answer(401), friday)                        # same week again
    cards.record_barns(answer(395), friday + timedelta(days=7))
    huss = cards.load_barns()["barns"]["1848"]
    assert [w["week"] for w in huss["weeks"]] == ["2026-W40", "2026-W39"]
    assert huss["weeks"][1]["prices"][2]["price"] == 401 and huss["city"] == "Kearney"


def test_a_page_per_barn_with_the_price_the_sheet_and_the_change(barns_file):
    cards.record_barns(answer(400), date(2026, 9, 18))
    cards.record_barns(answer(395), date(2026, 9, 25))
    site = build.build()
    page = (site / "barn-kearney-ne-1848.html").read_text(encoding="utf-8")
    assert "Huss Livestock Market" in page and "$395/cwt" in page
    assert "$5 from last week" in page and 'class="badge down"' in page  # fell: red, with an arrow and words
    assert "Heifers" in page and "800 lb" in page
    assert '<a href="barn-lexington-ne-1849.html">' in page               # other barns in the state
    assert 'content="Kearney, NE feeder cattle prices, week of' in page   # the search snippet leads with the town
    index = (site / "barns.html").read_text(encoding="utf-8")
    assert "barn-kearney-ne-1848.html" in index and "Nebraska" in index
    sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")
    assert "barns.html" in sitemap and "barn-kearney-ne-1848.html" in sitemap
    assert 'href="barns.html"' in (site / "index.html").read_text(encoding="utf-8")  # in the menu


def test_a_barn_that_stopped_selling_says_so(barns_file):
    cards.record_barns(answer(400, fresh=False, last_sale="2026-08-20"), date(2026, 9, 25))
    page = (build.build() / "barn-kearney-ne-1848.html").read_text(encoding="utf-8")
    assert "No sale in the last three weeks" in page and "$400/cwt" not in page


def test_the_steer_tile_links_to_the_barn_page(barns_file):
    cards.record_barns(answer(400), date(2026, 9, 25))
    import hero

    href = lambda slug: barn_pages.page_name(str(slug), cards.load_barns()["barns"][str(slug)])
    card = {"value": 400.0, "low": 376.0, "high": 420.0, "as_of": "2026-09-23", "market": "Huss", "market_slug": 1848}
    assert 'href="barn-kearney-ne-1848.html"' in hero.herd_tile(card, "Nebraska", href)
    assert 'href="herd-planner.html"' in hero.herd_tile({**card, "market_slug": None}, "Nebraska", href)


def test_no_barns_yet_still_builds_an_index(barns_file):
    site = build.build()
    assert "first prices arrive" in (site / "barns.html").read_text(encoding="utf-8")


def test_the_barn_list_fits_a_phone(barns_file):
    """Three columns (the town sits under the barn's name), so the price never hides off the right edge."""
    cards.record_barns(answer(400), date(2026, 9, 25))
    index = (build.build() / "barns.html").read_text(encoding="utf-8")
    assert "<th>Sale barn</th><th>Last sale</th><th>550 lb steer</th>" in index
    assert '<span class="barn-town">Kearney</span>' in index
