"""'Why Use Our Apps': every story is sourced, belongs to a real app, and shows up on the pages."""

import pytest

import build
import charts


@pytest.fixture
def site(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "OUT", tmp_path / "docs")  # a scratch build, never the real docs/
    return build.build()


def test_every_story_is_complete_and_sourced():
    apps = {a["id"] for a in build.load_apps()}
    for s in build.load_stories():
        assert s["app"] in apps, s["id"]
        for key in ("title", "headline", "chart_title", "takeaway", "caution", "source"):
            assert s[key].strip(), f"{s['id']} has no {key}"
        assert "notebook" in s["source"] or "README" in s["source"], f"{s['id']}: name the notebook or README"
        assert s["chart"] in charts.KINDS


def test_every_app_has_a_story():
    have = {s["app"] for s in build.load_stories()}
    assert {a["id"] for a in build.load_apps()} <= have


def test_charts_are_drawn_with_a_table_of_the_same_numbers():
    for s in build.load_stories():
        svg = charts.draw(s)
        assert svg.startswith('<svg class="chart"') and "<title>" in svg  # hover tooltips
        assert "Show the numbers" in charts.table(s)


def test_series_line_up():
    for s in build.load_stories():
        if s["chart"] == "seasonal":
            assert all(len(x["index"]) == len(s["months"]) == 12 for x in s["series"])
        if s["chart"] == "keep_rate":
            assert len(s["keep_pct"]) == len(s["reach_pct"])
        if s["chart"] == "ladder":
            assert len(s["steps"]) == len(s["r2"])
        if s["chart"] == "skill_by_date":
            assert len(s["dates"]) == len(s["skill"]) == len(s["typical_miss_pct"])
        if s["chart"] == "hire_wait":
            assert len(s["delay_days"]) == len(s["custom_cheapest_pct"])


def test_home_shows_every_story_and_app_pages_show_their_own(site):
    home = (site / "index.html").read_text(encoding="utf-8")
    assert "Why Use Our Apps" in home
    for s in build.load_stories():
        title = build.e(s["title"])  # as written into the HTML (an apostrophe becomes &#x27;)
        assert title in home
        page = (site / build.APP_PAGE.format(s["app"])).read_text(encoding="utf-8")
        assert title in page and "What the Numbers Show" in page


def test_every_story_says_how_to_read_its_chart():
    """Scott (2026-09-30): the charts on the app pages were too big and unexplained."""
    for s in build.load_stories():
        assert len(s.get("how_to_read", "")) > 40, s["id"]


def test_app_pages_show_their_charts_small_and_explained(site):
    for app in build.load_apps():
        page = (site / build.APP_PAGE.format(app["id"])).read_text(encoding="utf-8")
        own = [s for s in build.load_stories() if s["app"] == app["id"]]
        assert 'class="stories-compact' in page
        assert page.count('class="how-to-read"') == len(own)
        if len(own) > 1:
            assert 'class="stories-compact pair"' in page


def test_herd_planners_this_week_card_has_the_price_and_the_months(site):
    page = (site / "herd-planner.html").read_text(encoding="utf-8")
    week = build.cards.current()
    card = week["cards"].get("herd-planner")
    if not card:
        pytest.skip("no fresh steer price this week")
    assert 'class="stat-card week-card"' in page
    assert f'${card["value"]:,.0f}<small>/cwt</small>' in page
    assert "Sell now or wait?" in page and "<b>Now (" in page
    assert "full price sheet" in page          # links to the barn's own page


def test_herd_planners_this_week_is_a_slider_of_two_cards(site):
    """Scott (2026-09-30): This Week as a slider: the price + sell now or wait, then the barn's whole price sheet."""
    page = (site / "herd-planner.html").read_text(encoding="utf-8")
    if 'class="stat-card week-card"' not in page:
        pytest.skip("no fresh steer price this week")
    assert 'class="slider week-slider" data-slider data-dots' in page
    assert page.count('class="week-slide"') == 2
    assert "The whole price sheet" in page and "<summary>Show the numbers</summary>" in page
    assert 'src="slider.js?v=' in page


def test_the_findings_heading_is_a_band_with_one_headline(site):
    """Scott, 2026-10-07, of the plain heading: "This looks boring when it's something we should be proud of, and
    the customer should be happy to see." Now a deep-green band: "Why Use Our Apps" as a small gold line, one
    headline that makes the claim, and the sentence the cards have to keep (a source and a limit on each, which
    test_every_story_is_complete_and_sourced holds them to). The cards follow, outside the band."""
    home = (site / "index.html").read_text(encoding="utf-8")
    section = home[home.index('<section class="why" id="why">'):]
    section = section[:section.index("</section>")]
    band, cards = section.split('<div class="stories">')
    assert '<div class="why-band">' in band and '<p class="why-eyebrow">Why Use Our Apps</p>' in band
    assert "<h2>Answers You Can Check</h2>" in band and section.count("<h2") == 1
    assert band.index("why-eyebrow") < band.index("<h2>") < band.index('class="why-lede"')
    assert 'class="story"' in cards and "why-band" not in cards
    css = (build.STATIC / "site.css").read_text(encoding="utf-8")
    assert ".why-band { background: var(--suite-deep-green);" in css
    # The link is the suite's gold, like the small line above the headline (Scott picked it over white and two
    # yellow-greens, 2026-10-07): one accent on the band, not two.
    assert ".why-lede a { color: var(--suite-gold);" in css and ".why-eyebrow {" in css
    assert "color: var(--suite-gold); }" in css[css.index(".why-eyebrow {"):css.index(".why-band h2")]
