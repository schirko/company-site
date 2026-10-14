"""Weekly market news pages (markets.py): built from USDA's reports saved with each barn's weekly sheet.

The Nebraska answers are Herd Planner's real /suite/barns of 2026-10-14 (tests/data), so the expected words and numbers
below can be checked against USDA's own reports: North Platte 951 head on Oct 13 (1,132 a week before, 850 a year
before), Bassett 1,045 on Oct 7, Burwell 2,090 on Oct 2, Gordon no sale since Nov 2, 2024."""

import copy
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

import build
import cards
import markets

LIVE = json.loads((Path(__file__).parent / "data" / "suite-barns-2026-10-14.json").read_text(encoding="utf-8"))
FRIDAY = date(2026, 10, 16)  # the weekly job's run that will first save these reports: 2026-W42


@pytest.fixture
def barns_file(tmp_path, monkeypatch):
    monkeypatch.setattr(cards, "BARNS_FILE", tmp_path / "barns.json")
    monkeypatch.setattr(cards, "WEEKS", tmp_path / "weeks.json")
    monkeypatch.setattr(build, "OUT", tmp_path / "docs")
    return tmp_path / "barns.json"


def no_reports(body):
    body = copy.deepcopy(body)
    for b in body["barns"]:
        b.pop("report", None)
    return body


def test_the_refresh_keeps_each_barns_usda_report(barns_file):
    cards.record_barns(LIVE, FRIDAY)
    week = cards.load_barns()["barns"]["3653"]["weeks"][0]
    assert week["report"]["head_sold"] == 951 and week["report"]["sale_date"] == "2026-10-13"
    assert set(week["report"]) == set(cards.REPORT_KEYS)
    assert "report" not in cards.load_barns()["barns"]["3801"]["weeks"][0]   # Gordon: none sent, none kept
    cards.record_barns(no_reports(LIVE), FRIDAY + timedelta(days=7))        # an older Herd Planner: no report key
    assert "report" not in cards.load_barns()["barns"]["3653"]["weeks"][0]


def test_the_nebraska_page_reads_like_the_mockup(barns_file):
    cards.record_barns(LIVE, FRIDAY)
    site = build.build()
    page = (site / "markets-ne.html").read_text(encoding="utf-8")
    assert page == (site / "markets-ne-2026-w42.html").read_text(encoding="utf-8").replace(
        "markets-ne-2026-w42.html", "markets-ne.html")
    assert "Nebraska Cattle Markets: Week of Oct 12</h1>" in page
    # the opening line: newest sale, USDA's own week-ago and year-ago counts, the summary quoted as written
    assert ("North Platte sold 951 head on Tue, Oct 13, 16% fewer than the week before and 12% more than a year ago. "
            "USDA&rsquo;s market reporter: &ldquo;Compared to last week, steer and heifer calves sold with a lower "
            "undertone.&rdquo;") in page
    assert ">4,086<" in page and "At 3 Nebraska barns, Oct 2 to Oct 13" in page          # 951 + 1,045 + 2,090
    assert "$432&ndash;$450<small>/cwt</small>" in page and "About $2,376 to $2,473 a head" in page
    # newest sale first
    assert page.index("North Platte Stockyards") < page.index("Bassett Livestock Auction") < page.index("Burwell Livestock Market")
    assert "23% fewer" not in page and "No sale a year before" in page                  # Burwell: 0 a year ago
    assert "49%</b> fewer than a week before (2,055)" in page and "375%</b> more than a week before (440)" in page
    assert "Majority of the calves had fall precondition shots." in page                  # the narrative, as written
    assert 'href="https://mymarketnews.ams.usda.gov/viewReport/3653"' in page
    assert "Gordon Livestock Market</a></b>: no sale reported in the last three weeks; its last in our data was Sat, Nov 2, 2024." in page
    assert 'href="barn-north-platte-ne-3653.html"' in page                                 # our price sheet for it
    assert "badge down" not in page and "#a4262c" not in page                              # head counts are neutral
    assert "Oklahoma" not in page.split("<main")[1].split("</main>")[0]                   # one state per page


def test_next_sale_dates_come_from_the_reporters_words():
    rep = lambda text, sold="2026-10-07": {"narrative": text, "sale_date": sold}
    assert markets.next_sale(rep("Next Auction Dates Oct 14th Special Feeder Cattle Auction, Oct 21st")) == date(2026, 10, 14)
    assert markets.next_sale(rep("... Next Auction Date Oct 16th 23rd & 30th Spring Calf", "2026-10-02")) == date(2026, 10, 16)
    assert markets.next_sale(rep("Next sale date: January 5", "2026-12-15")) == date(2027, 1, 5)   # into next year
    assert markets.next_sale(rep("No sale next week.")) is None
    assert markets.next_sale(rep("Next Auction Date Feb 30th")) is None                      # not a date


def test_the_next_sales_tile_shows_only_dates_after_the_run(barns_file):
    cards.record_barns(LIVE, date(2026, 10, 9))             # a run before both named dates
    page = (build.build() / "markets-ne.html").read_text(encoding="utf-8")
    assert "Next sales, per USDA&rsquo;s reports" in page and "Oct 14 &middot; Oct 16" in page
    assert "Bassett, Wed<br>Burwell, Fri" in page
    cards.record_barns(LIVE, FRIDAY)                         # Friday 7 am: Burwell's sale that day is still ahead
    page = (build.build() / "markets-ne.html").read_text(encoding="utf-8")
    assert "Oct 16</p>" in page and "Burwell, Fri" in page and "Bassett, Wed" not in page
    cards.record_barns(LIVE, FRIDAY + timedelta(days=1))     # after both (a Saturday re-run): the tile counts barns
    page = (build.build() / "markets-ne.html").read_text(encoding="utf-8")
    assert "Next sales" not in page and "Barns reporting" in page and ">3 of 4<" in page


def test_saved_weeks_stay_as_they_were_and_are_listed(barns_file):
    cards.record_barns(LIVE, FRIDAY)
    first = (build.build() / "markets-ne-2026-w42.html").read_text(encoding="utf-8")
    later = copy.deepcopy(LIVE)
    np = next(b for b in later["barns"] if b["slug"] == 3653)
    np["last_sale"], np["report"] = "2026-10-20", {**np["report"], "sale_date": "2026-10-20", "head_sold": 1200,
                                                   "head_week_ago": 951, "summary": "Steady.", "narrative": "Steady."}
    cards.record_barns(later, FRIDAY + timedelta(days=7))
    site = build.build()
    assert (site / "markets-ne-2026-w42.html").read_text(encoding="utf-8") == first
    newest = (site / "markets-ne.html").read_text(encoding="utf-8")
    assert "Week of Oct 19</h1>" in newest and "North Platte sold 1,200 head on Tue, Oct 20" in newest
    assert '<a href="markets-ne-2026-w42.html">Week of Oct 12</a>' in newest
    sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")
    for name in ("markets-ne.html", "markets-ne-2026-w42.html", "markets-ne-2026-w43.html"):
        assert name in sitemap


def test_no_page_without_a_fresh_sale_with_a_report(barns_file):
    cards.record_barns(no_reports(LIVE), FRIDAY)             # prices but no reports (before Herd Planner v0.48)
    site = build.build()
    assert not list(site.glob("markets-*.html"))
    assert "This Week&rsquo;s Markets" not in (site / "barns.html").read_text(encoding="utf-8")
    stale = copy.deepcopy(LIVE)
    for b in stale["barns"]:
        b["fresh"] = False
    cards.record_barns(stale, FRIDAY + timedelta(days=7))
    assert markets.weeks_with_news(cards.load_barns()["barns"], "NE") == []


def test_barn_prices_links_the_state_page(barns_file):
    cards.record_barns(LIVE, FRIDAY)
    index = (build.build() / "barns.html").read_text(encoding="utf-8")
    assert "This Week&rsquo;s Markets" in index
    assert '<a href="markets-ne.html">Nebraska Cattle Markets</a>, week of Oct 12' in index


def test_usda_internal_markers_are_dropped_but_the_words_kept():
    assert markets.clean("Demand good.  *** Add Close ***  Quality average.") == "Demand good. Quality average."
    assert markets.clean(None) == ""


def test_a_barn_that_sold_without_a_report_says_so(barns_file):
    body = copy.deepcopy(LIVE)
    next(b for b in body["barns"] if b["slug"] == 1852)["report"] = None   # Bassett sold, report missing
    cards.record_barns(body, FRIDAY)
    page = (build.build() / "markets-ne.html").read_text(encoding="utf-8")
    assert "Bassett Livestock Auction</a></b>: sold on Wed, Oct 7; USDA&rsquo;s report of that sale isn&rsquo;t in our data." in page
    assert ">3,041<" in page                                    # 951 + 2,090: only reported sales are added up
