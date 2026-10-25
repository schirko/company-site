"""Why We Built This: the drought story on the home page (2026-10-16, content/drought.json).

Scott: "The 2020ish draughts caused crop and feed growing issues which led to cattle numbers issues. That's how herd
planner started so I want to refer to it in the apps." He chose A of notes/site-why-we-built-this-2026-10-16.png:
the whole story on the home page. Every number names its source; these tests keep it that way."""

import re

import pytest

import build
import charts

D = build.load_drought()


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "OUT", tmp_path / "docs")  # a scratch build, never the real docs/
    build.build()
    return (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")


def test_every_step_and_the_chart_name_a_source():
    assert len(D["steps"]) == 5
    for s in D["steps"]:
        assert s["title"].strip() and s["text"].strip() and s["source"].strip(), s["title"]
        assert re.search(r"\d", s["text"]), f"{s['title']}: a step carries its number"
    assert "USDA NASS" in D["chart"]["source"] and "revised" in D["chart"]["source"]
    assert D["caution"].strip()                                       # not all of the drop was drought


def test_the_chart_numbers_and_the_words_agree():
    ch = D["chart"]
    years, cows = ch["years"], ch["beef_cows_thousand"]
    assert len(years) == len(cows) and years == sorted(years) and years == list(range(years[0], years[-1] + 1))
    first, last = cows[0], cows[-1]
    fewer, pct = (first - last) / 1000, (first - last) / first * 100
    assert f"{fewer:.1f} million fewer from {years[0]} to {years[-1]}" in ch["change"]
    assert f"down {pct:.0f}%" in ch["change"] and "our arithmetic" in ch["change"]
    herd = D["steps"][-1]["text"]
    assert f"**{first / 1000:.1f} million** beef cows in {years[0]}" in herd and f"**{last / 1000:.1f} million** in {years[-1]}" in herd
    lo, hi = ch["drought_years"]
    assert years[0] < lo <= hi < years[-1]


def test_no_claim_without_a_primary_source():
    """'Lowest since 1951' is repeated widely, but the NASS reports don't say it (claude/drought-plan.md)."""
    words = str(D).lower()
    assert "1951" not in words and "lowest since" not in words


def test_the_chart_is_drawn_from_zero_with_a_table_of_the_same_numbers():
    svg, table = charts.herd_size(D["chart"]), charts.herd_size_table(D["chart"])
    assert svg.count("<title>") == len(D["chart"]["years"])         # every bar says its value on hover
    assert ">0</text>" in svg                                         # bars start at zero: the drop isn't exaggerated
    assert "Drought years, 2020 to 2023" in svg
    for y, v in zip(D["chart"]["years"], D["chart"]["beef_cows_thousand"]):
        assert f"<td>{y}</td><td>{v:,.1f}</td>" in table


def test_the_story_sits_above_built_in_with_links_to_the_apps(home):
    at = home.index('id="why-we-built-this"')
    assert home.index("<h2>Our Promises</h2>") < at < home.index("<h2>Built in Centennial, Colorado</h2>")
    section = home[at:home.index("</section>", at)]
    assert "<h2>Drought Is Why These Apps Exist</h2>" in section
    assert '<a href="grazing-planner.html">' in section and '<a href="herd-planner.html">' in section
    assert '<a href="farm-equipment-planner.html">Farm Equipment Planner</a></strong>: What your combine costs per bushel' \
        in section                                                    # v0.36.0's In a Short Year (2026-10-17)
    assert "Hay &amp; Feed Planner</strong>: Coming" in section     # not built yet: named, not linked
    assert "<strong>61%</strong>" in section and "<li><h3>" in section
    assert ("Draft for Scott to rewrite" in section) == bool(D["draft"])


# --- What hay cost in Nebraska (2026-10-24; Scott chose A of notes/hay-chart-*-2026-10-24.png) ---------------------

HC, PRICES = D["hay_chart"], build.load_hay_prices()


def test_the_hay_numbers_line_up_and_name_their_source():
    m, g, a = PRICES["months"], PRICES["grass"], PRICES["alfalfa"]
    assert len(m) == len(g) == len(a) >= 60 and m == sorted(m)
    assert all(20 < v < 1000 for v in g + a)
    assert "Nebraska Direct Hay Report" in HC["source"] and "2935" in HC["source"]
    assert HC["caution"].strip() and HC["method"].strip()


def test_the_callouts_are_the_numbers_on_the_chart():
    """The Grazing Planner's warning ($156 at the July 1, 2022 check, about $215 that winter) is what the chart shows."""
    for c in HC["callouts"]:
        assert PRICES["grass"][PRICES["months"].index(c["month"])] == c["price"]
        assert f"${c['price']}" in c["words"] and f"${c['price']}" in HC["change"]


def test_the_card_sits_under_the_steps_with_both_charts_and_the_numbers(home):
    sec = home[home.index('id="why-we-built-this"'):]
    assert sec.index('<ol class="dr-steps">') < sec.index('id="hay-prices"') < sec.index('class="dr-help"')
    card = sec[sec.index('id="hay-prices"'):sec.index('class="dr-help"')]
    assert card.count('<svg class="chart hay-chart"') == 2                  # wide, and narrow for phones
    assert card.count("<tr>") == len(PRICES["months"]) + 1                  # Show the numbers: every month
    assert "grazing-planner.html" in card and "hauling is extra" in card
    assert "Grazing Planner</a></strong>: How many head your grass can carry this season, how often a season like it runs short, and what the hay would cost if it does." in sec


def test_the_refresh_keeps_each_months_last_report():
    import importlib.util
    spec = importlib.util.spec_from_file_location("hay_prices", build.ROOT / "tools" / "hay_prices.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    p = lambda v: {"price": v}
    hay = {"window_weeks": 8, "source": "USDA", "weeks": {
        "2022-06-17": {"grass": p(150), "alfalfa": p(170)}, "2022-06-24": {"grass": p(156), "alfalfa": p(173)},
        "2022-07-01": {"grass": p(160), "alfalfa": None}}}                  # no alfalfa: the month is left out
    got = mod.monthly(hay)
    assert (got["months"], got["grass"], got["alfalfa"]) == (["2022-06"], [156], [173])
