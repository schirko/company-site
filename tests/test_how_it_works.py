"""How It Works on the Herd Planner page.

2026-10-16: the five steps became the ranch year (Scott: the steps made Herd Planner "sound like all it does is selling
and growing"; B of notes/site-herd-planner-how-it-works-2026-10-16.png). 2026-10-18: the four How It Works cards took
that strip's place (Scott: "B is good", notes/hp-how-B-desk-2026-10-18.png), because "Herd Planner Through the Ranch
Year" just above already tells the year, season by season."""

import pytest

import build


@pytest.fixture
def page(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "OUT", tmp_path / "docs")  # a scratch build, never the real docs/
    build.build()
    return (tmp_path / "docs" / "herd-planner.html").read_text(encoding="utf-8")


def test_the_cards_follow_the_ranch_year_in_the_strips_place(page):
    year = page.index("Herd Planner Through the Ranch Year</h2>")
    cards = page.index('<h2 id="how-h">How Herd Planner Works</h2>')
    way_in = page.index('<div class="steps-cta">')
    assert year < cards < way_in < page.index('<h2 class="found-h">What We Found</h2>')
    assert 'class="lp-steps lp-year"' not in page and "lp-steps-sub" not in page   # the five-season strip is gone


def test_the_way_in_comes_once_after_the_cards(page):
    at = page.index('<section class="how" id="how-it-works"')
    assert 'class="how-go"' not in page[at:page.index("</section>", at)]   # no second Join the Waitlist right above it
    assert "Step 1 is picking the barn" not in page
    assert "<strong>Ready for your own herd?</strong> Start with your ranch and the barn you sell at." in page
