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
