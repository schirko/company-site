"""How It Works on the Herd Planner page as the ranch year (2026-10-16).

Scott: the five steps made Herd Planner "sound like all it does is selling and growing, but that's more of what it
was when we started, not what it is now." He chose B of notes/site-herd-planner-how-it-works-2026-10-16.png."""

import pytest

import build


@pytest.fixture
def page(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "OUT", tmp_path / "docs")  # a scratch build, never the real docs/
    build.build()
    return (tmp_path / "docs" / "herd-planner.html").read_text(encoding="utf-8")


def test_the_herd_planner_page_tells_the_ranch_year(page):
    at = page.index("<h2>How It Works</h2>")
    part = page[at:page.index("</ol>", at)]
    assert '<p class="lp-steps-sub">A year with Herd Planner</p>' in part and 'class="lp-steps lp-year"' in part
    seasons = [part.index(f"<li><b>{s}</b>") for s in ("Calving", "Summer", "Fall", "Sale Day", "Winter")]
    assert seasons == sorted(seasons)
    for feature in ("Sale Sheet", "Lender Report", "This Week", "keep or sell"):
        assert feature in part, feature


def test_the_way_in_no_longer_says_step_1_is_the_barn(page):
    assert "Step 1 is picking the barn" not in page
    assert "<strong>Ready for your own herd?</strong> Start with your ranch and the barn you sell at." in page
