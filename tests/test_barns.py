"""One page per sale barn: saved weekly from Herd Planner, one page each, an index, honest when stale."""

import json
from pathlib import Path
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
    assert 'content="Kearney, NE feeder cattle prices, estimated for the week of Sep 25, 2026' in page   # town first
    assert "<title>Huss Livestock Market, Kearney, NE: Feeder Cattle Prices, Week of Sep 25, 2026 |" in page
    assert "550 lb steer, estimate for the week of Sep 25" in page and "Last sale here" in page
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
    assert "<th>Sale barn</th><th>Last sale</th><th>550 lb steer, week of Sep 25</th>" in index
    assert '<span class="barn-town">Kearney</span>' in index


SEASON = {"key": "calves", "label": "Steer calves, 500-600 lb", "own_months": True, "sells_months": list(range(1, 13)),
          "best": 3, "worst": 11, "spread_pct": 11.1, "clear": True, "markets": 6,
          "typical": [{"month": m, "index": 1 + d / 100, "low": 1 + (d - 3) / 100, "high": 1 + (d + 3) / 100}
                      for m, d in zip(range(1, 13), (1, 2, 5, 3, 2, 2, 2, 1, -3, -4, -6, -4))],
          "this_season": [{"month": f"{y}-{m:02d}", "ratio": 1.0} for y, m in
                          [(2025, 10), (2025, 11), (2025, 12)] + [(2026, m) for m in range(1, 10)]]}


def test_a_barn_page_shows_its_best_months_to_sell(barns_file):
    body = answer(400)
    body["barns"][0]["seasons"] = [SEASON]
    cards.record_barns(body, date(2026, 9, 25))
    page = (build.build() / "barn-kearney-ne-1848.html").read_text(encoding="utf-8")
    assert "Best Months to Sell" in page and "typically bring the most in <strong>Mar</strong>" in page
    assert "a typical Sep runs -3%" in page and "This season, last 12 months" in page
    # The axis ends at this season's newest month, so the line runs left to right: Oct first, Sep last.
    chart = page[page.index("Steer calves, 500-600 lb at"):]
    assert chart.index(">Oct<") < chart.index(">Jan<") < chart.index(">Sep<")
    other = (build.build() / "barn-lexington-ne-1849.html").read_text(encoding="utf-8")
    assert "Best Months to Sell" not in other  # no seasons from Herd Planner: no section


def test_a_fall_only_barn_says_it_has_no_pattern_of_its_own(barns_file):
    body = answer(400)
    body["barns"][0]["seasons"] = [dict(SEASON, own_months=False, sells_months=[10, 11], this_season=[])]
    cards.record_barns(body, date(2026, 9, 25))
    page = (build.build() / "barn-kearney-ne-1848.html").read_text(encoding="utf-8")
    assert "mainly in Oct and Nov: too few months for a pattern of its own" in page
    assert "compared with this year's own trend line" not in page  # no line, so no note about it


def test_seasons_survive_a_week_when_herd_planner_sends_none(barns_file):
    body = answer(400)
    body["barns"][0]["seasons"] = [SEASON]
    cards.record_barns(body, date(2026, 9, 18))
    cards.record_barns(answer(401), date(2026, 9, 25))  # an older Herd Planner: no seasons this week
    assert cards.load_barns()["barns"]["1848"]["seasons"][0]["best"] == 3


def test_every_barn_page_says_how_to_reach_the_barn(barns_file):
    """Scott, 2026-10-12: "add contact information to each barn on their page". Every page has Contact the Barn with
    a map link and USDA's page for the sale; checked business details show only with their source and date."""
    import json
    cards.record_barns(answer(400), date(2026, 9, 25))
    site = build.build()
    for page in site.glob("barn-*.html"):
        html = page.read_text(encoding="utf-8")
        assert '<h2 id="contact">Contact the Barn</h2>' in html and 'href="#contact">Contact the Barn</a>' in html and "google.com/maps/search/?api=1&amp;query=" in html, page.name
        assert "mymarketnews.ams.usda.gov/viewReport/" in html and "call the barn before you" in html, page.name
    listed = json.loads(barn_pages.CONTACTS.read_text(encoding="utf-8"))["barns"]
    for slug, c in listed.items():
        assert c.get("source") and c.get("source_url", "").startswith("https://") and c.get("checked"), slug
        assert set(c) <= {"address", "phone", "website", "source", "source_url", "checked"}, slug


def test_checked_details_show_with_their_source():
    barn = {"name": "North Platte Stockyards", "city": "North Platte", "state": "NE"}
    html = barn_pages.contact_section("3653", barn, {"3653": {
        "address": "2200 E 8th Street, North Platte, NE 69101", "phone": "(308) 555-0100",
        "source": "A listing", "source_url": "https://example.com/x", "checked": "2026-10-12"}})
    assert "2200 E 8th Street" in html and 'href="tel:3085550100"' in html
    assert 'Details from <a href="https://example.com/x" rel="noopener">A listing</a>, checked Oct 12.' in html
    bare = barn_pages.contact_section("1851", {"name": "Burwell Livestock Market", "city": "Burwell", "state": "NE"}, {})
    assert "Address" not in bare and "Phone" not in bare and "viewReport/1851" in bare


def test_contact_link_sits_in_the_lede():
    """2026-10-20, Scott: the contact link should be "up top after the text: 'Brush, CO · Cattle Auction. Feeder cattle
    prices, worked out every Friday from USDA auction reports.' Just a simple" link."""
    import barn_pages
    src = Path(barn_pages.__file__).read_text(encoding="utf-8")
    assert 'worked out every Friday from USDA auction reports. <a class="lede-link" href="#contact">Contact the Barn</a></p>' in src
    assert '<h2 id="contact">Contact the Barn</h2>' in src


def test_contact_the_barn_is_at_the_bottom():
    """2026-10-20, Scott: the quick link up top "should just link to the bottom of the page where all the contact info
    lives"."""
    import barn_pages
    src = Path(barn_pages.__file__).read_text(encoding="utf-8")
    body = src[src.index('<h2>Where the Numbers Come From</h2>'):]
    assert '<div class="barn-contact-box card">{contact_section(slug, barn, load_contacts())}</div>\n  </div>\n</section>' in body


def test_barns_can_post_a_notice_and_ask_to_update_their_page(barns_file):
    """2026-10-20, Scott: barns "modify their profile and maybe post a current message"; the small start he chose
    (notes/site-claim-*-2026-10-20.png, "looks great"). The page reads the notice from My Farm; the form is My Farm's."""
    import json
    import config
    cards.record_barns(answer(400), date(2026, 9, 25))
    site = build.build()
    page = next(site.glob("barn-*.html")).read_text(encoding="utf-8")
    assert '<div class="barn-notice" id="barn-notice" role="note" hidden data-src="https://apps.cornerpostlogic.com/barns/' in page
    assert '<script src="barn-notice.js?v=' in page and "/barn-update.html?barn=" in page and ">Update This Page</a>" in page
    listed = json.loads((site / "barn-list.json").read_text(encoding="utf-8"))
    assert listed["format"] == 1 and listed["barns"]
    for slug, b in listed["barns"].items():
        assert b["name"] and b["page"].startswith(config.SITE_URL) and set(b) == {"name", "place", "phone", "page", "last_sale", "steer", "lat", "lon"}
        assert b["last_sale"] == "" or date.fromisoformat(b["last_sale"]) <= date.today()   # the page's newest sale
    js = (Path(build.__file__).parent / "static" / "barn-notice.js").read_text(encoding="utf-8")
    assert "innerHTML" not in js and 'credentials: "omit"' in js
    privacy = (site / "privacy.html").read_text(encoding="utf-8")
    assert 'id="barn-requests"' in privacy


def test_the_barn_list_carries_this_weeks_steer_for_my_farm(barns_file):
    """2026-10-23 (Scott chose farm-account/notes/from-barns-cards-*-2026-10-23.png): My Farm's From Your Barns shows
    each barn's 550 lb steer when there are no notices. The same numbers the barn's page shows, with the change from
    last week in whole dollars; nothing for a barn that hasn't sold in three weeks."""
    cards.record_barns(answer(400), date(2026, 9, 18))
    cards.record_barns(answer(395), date(2026, 9, 25))
    site = build.build()
    huss = json.loads((site / "barn-list.json").read_text(encoding="utf-8"))["barns"]["1848"]["steer"]
    page = (site / "barn-kearney-ne-1848.html").read_text(encoding="utf-8")
    assert f"{barn_pages.money(huss['price'])}/cwt" in page and barn_pages.money(huss["low"]) in page
    assert (huss["change"], huss["hub"], huss["sale"]) == (-5, False, "2026-09-23")
    assert huss["week"] == cards.load_barns()["barns"]["1848"]["weeks"][0]["date"]
    cards.record_barns(answer(390, fresh=False), date(2026, 10, 2))
    site = build.build()
    assert json.loads((site / "barn-list.json").read_text(encoding="utf-8"))["barns"]["1848"]["steer"] is None


def test_barn_pages_have_follow_this_barn(barns_file):
    """2026-10-20 (claude/barn-plan.md Part 2; Scott chose A of farm-account/notes/barn-alerts-*): Follow This Barn under
    the top line. Without JavaScript or signed out it is a link to My Farm (#follow/<barn>), which signs you in and asks;
    signed in, a box here asks, its email box unticked."""
    import re
    cards.record_barns(answer(400), date(2026, 9, 25))
    site = build.build()
    page = next(site.glob("barn-*.html")).read_text(encoding="utf-8")
    slug = re.search(r'data-barn="(\d+)"', page).group(1)
    assert f'<a class="btn-follow" id="bf-button" href="https://apps.cornerpostlogic.com/#follow/{slug}">' in page
    assert page.index('id="barn-follow"') < page.index('id="barn-notice"')        # under the lede, above the notice
    assert '<input type="checkbox" id="bf-email"> Email me this barn\'s notices' in page
    assert "We never give your name or email to the barn." in page and '<script src="barn-follow.js?v=' in page
    js = (Path(build.__file__).parent / "static" / "barn-follow.js").read_text(encoding="utf-8")
    assert "innerHTML" not in js and 'credentials: "include"' in js and "email.checked = false;" in js
    assert '"/site/barns/" + encodeURIComponent(barn) + "/follow"' in js and 'method: "POST"' in js
    assert "headers:" not in js                                                     # a simple request: no preflight
    privacy = (site / "privacy.html").read_text(encoding="utf-8")
    assert 'id="barn-follows"' in privacy and "never sees who follows it" in privacy


def test_barn_logos_show_beside_the_name_once_approved(barns_file):
    """2026-10-21 (claude/barn-plan.md Part 1 step 2; Scott chose A of farm-account/notes/barn-logo-*): left of the name
    on the barn's page and tiny on the Barn Prices list; read from My Farm (no cookie), hidden until there is one."""
    import re
    cards.record_barns(answer(400), date(2026, 9, 25))
    site = build.build()
    page = next(site.glob("barn-*.html")).read_text(encoding="utf-8")
    assert re.search(r'<div class="barn-title"><img class="barn-logo" id="barn-logo" data-barn="\d+" '
                     r'data-barn-logos="https://apps.cornerpostlogic.com" alt="" width="56" height="56" hidden><h1>', page)
    assert '<script src="barn-logo.js?v=' in page
    listing = (site / "barns.html").read_text(encoding="utf-8")
    assert re.search(r'<a href="barn-[a-z-]+-\d+\.html" data-barn="\d+">', listing) and '<script src="barn-logo.js?v=' in listing
    js = (Path(build.__file__).parent / "static" / "barn-logo.js").read_text(encoding="utf-8")
    assert "innerHTML" not in js and 'credentials: "omit"' in js and '"/barn-logos"' in js



def test_privacy_says_barn_pages_are_counted(barns_file):
    """2026-10-21 (barn plan step 3): barn page views are a count per day, nothing about the visitor."""
    cards.record_barns(answer(400), date(2026, 9, 25))
    site = build.build()
    privacy = (site / "privacy.html").read_text(encoding="utf-8")
    assert 'id="barn-views"' in privacy and "Only the" in privacy and "never who" in privacy


def test_the_sale_calendar_and_the_two_ways_card(barns_file):
    """2026-10-21, Scott: "B is good" (the month grid, farm-account/notes/barn-cal-2-B-*) and, of the barn version of the
    plans card, "Looks good" (barn-two-ways-*). The calendar is read from My Farm when the page opens; the card says what
    a barn gets free and what a barn account adds, and never offers a better price."""
    cards.record_barns(answer(400), date(2026, 9, 25))
    site = build.build()
    page = next(site.glob("barn-*.html")).read_text(encoding="utf-8")
    assert 'id="barn-calendar"' in page and 'data-src="https://apps.cornerpostlogic.com/barns/' in page and "/calendar\"" in page
    assert '<script src="barn-calendar.js?v=' in page
    assert page.index('id="barn-notice"') < page.index('id="barn-calendar"') < page.index("<h2>The Last 12 Weeks</h2>")
    card = page[page.index('<section class="two-ways"'):]
    assert "Two Ways to Run Your Barn&rsquo;s Page" in card and "Free During the Pilot" in card
    assert "&amp;account=1" in card and "Ask for a Barn Account" in card and "Run this barn?" not in page
    assert "no barn can pay for a better price" in card
    assert card.count('aria-label="Yes"') == 2 * 4 + 6 and card.count('aria-label="No"') == 6
    js = (Path(build.__file__).parent / "static" / "barn-calendar.js").read_text(encoding="utf-8")
    assert "innerHTML" not in js and 'credentials: "omit"' in js
    privacy = (site / "privacy.html").read_text(encoding="utf-8")
    assert 'id="barn-calendar"' in privacy and "Barn sale calendars and reminders" in privacy


def test_add_to_my_phones_calendar(barns_file):
    """2026-10-21, Scott: "A looks good" (farm-account/notes/barn-ics-*): one button under the month grid that opens
    iPhone or Mac (webcal), Google Calendar and the address to copy: a subscription to My Farm's calendar.ics."""
    js = (Path(build.__file__).parent / "static" / "barn-calendar.js").read_text(encoding="utf-8")
    assert 'src + ".ics"' in js and 'replace(/^https?:/, "webcal:")' in js
    assert "calendar.google.com/calendar/r?cid=" in js and "Add to My Phone" in js and "innerHTML" not in js
    assert "choose Other calendars, then + and From URL" in js        # the Android app can't add one from a link
    cards.record_barns(answer(400), date(2026, 9, 25))
    privacy = (build.build() / "privacy.html").read_text(encoding="utf-8")
    assert "Add to My Phone&rsquo;s Calendar" in privacy and "nothing\n        about you or your phone is kept or counted" in privacy
