"""docs/week.json (2026-10-17): the county of the week for My Farm's sign-in page, the same week this site shows."""

import json


def test_the_week_is_published_for_my_farm(tmp_path, monkeypatch):
    import build
    import cards

    monkeypatch.setattr(build, "OUT", tmp_path / "docs")
    site = build.build()
    data = json.loads((site / "week.json").read_text(encoding="utf-8"))
    week = cards.current()
    assert data["format"] == 1
    assert data["week"] == week["week"] and data["place"] == week["place"] and data["cards"] == week["cards"]
    assert {"fips", "county", "state", "state_name"} <= set(data["place"])
    for card in data["cards"].values():
        if card:
            assert card["headline"] and card["source"]      # every number with its source
    assert len((site / "week.json").read_bytes()) < 20_000
