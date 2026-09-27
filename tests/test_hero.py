"""The live panel: red marks the downside, never alone, and the rounded numbers agree."""

import re

import hero

WEEK = {"week": "2026-W39", "date": "2026-09-25",
        "place": {"fips": "31063", "state": "NE", "county": "Frontier County", "state_name": "Nebraska"},
        "cards": {"herd-planner": None,
                  "corn-yield-predictor": {"label": "Trend corn yield, 2026", "headline": "146 bu/acre",
                                           "value": 146.4, "low": 128.2},
                  "farm-equipment-planner": {"label": "Fall field days, Oct 1 to Nov 30", "headline": "55 of 61 days",
                                             "value": 55.0, "low": 48.5}}}
SEASON = {"chart": "seasonal", "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
          "series": [{"name": "calves", "index": [1.011, 1.025, 1.049, 1.033, 1.004, 1.022, 1.016, 1.015,
                                                  0.959, 0.940, 0.944, 0.980]}]}


def build():
    return hero.panel(WEEK, [SEASON], lambda iso: iso)


def test_field_day_numbers_add_up_to_61():
    html = build()
    wet = int(re.search(r"workable even in a wet fall \((\d+)\)", html).group(1))
    lost = int(re.search(r"(\d+) lost in a wet fall", html).group(1))
    assert wet + lost == 61
    assert html.count(f'fill="{hero.BLUE}"') >= wet  # one dark square per workable wet-fall day


def test_red_always_comes_with_an_arrow_and_words():
    html = build()
    for flag in re.findall(r'<span class="badge down">(.*?)</span>\s', html):
        assert "▼" in flag
    assert "below trend" in html  # September calves run 4% under the trend


def test_missing_price_is_said_plainly():
    assert "No fresh price" in build()
