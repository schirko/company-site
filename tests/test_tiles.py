"""The home page's app tiles: this week's number top right; at the bottom, Open and one way in for someone new
(and later the price)."""

import build
import cards
import config

APP = {"id": "grazing-planner", "name": "Grazing Planner", "url": "https://grazing-planner.onrender.com/"}
SOON = {"id": "farm-equipment-planner", "name": "Farm Equipment Planner", "url": None}
COPY = {"question": "How much grass?", "price_from": "$9"}
PLACE = {"fips": "31063", "state": "NE", "county": "Frontier County", "state_name": "Nebraska"}


def week(**cards_):
    return {"week": "2026-W39", "date": "2026-09-27", "place": PLACE, "cards": cards_}


def grass(value):
    return {"value": value, "season": 2026, "detail": "Frontier County, NE grassland: about 1,904 lb an acre."}


def test_a_grass_shortfall_is_red_with_an_arrow_and_words():
    tile = build.app_tile(APP, COPY, week(**{cards.GRAZE: grass(-0.081)}))
    assert '<b class="down">▼ 8%</b> below normal' in tile
    assert "Frontier Co. grass, 2026" in tile


def test_more_grass_than_normal_is_not_red():
    tile = build.app_tile(APP, COPY, week(**{cards.GRAZE: grass(0.12)}))
    assert '<b class="">▲ 12%</b> above normal' in tile and "down" not in tile


def test_a_week_without_a_number_leaves_the_corner_empty():
    tile = build.app_tile(APP, COPY, week())  # an Iowa county: the Grazing Planner covers Nebraska only
    assert "tile-stat" not in tile and "Grazing Planner" in tile


def test_the_steer_price_names_its_barn():
    herd = {"value": 462.52, "market": "Bassett Livestock Auction, Bassett NE", "detail": "About $2,544 a head."}
    tile = build.app_tile({**APP, "id": cards.HERD}, COPY, week(**{cards.HERD: herd}))
    assert "<b class=\"\">$463</b>/cwt" in tile and "550 lb steer, Bassett NE" in tile


def test_no_prices_until_billing_exists(monkeypatch):
    monkeypatch.setattr(config, "SHOW_PRICES", False)
    assert "/mo" not in build.app_tile(APP, COPY, week()) + build.app_tile(SOON, COPY, week())
    assert "Free to try" in build.app_tile(APP, COPY, week())
    monkeypatch.setattr(config, "SHOW_PRICES", True)
    tile = build.app_tile(APP, COPY, week())
    assert "From <b>$9/mo</b>" in tile
    assert "Plan from" not in tile   # the paid level is a subscription, never "the plan" (Scott, 2026-10-04)
    soon = build.app_tile(SOON, COPY, week())
    assert "Coming soon" in soon and "Free to try" not in soon  # nothing to try yet


def test_every_app_has_a_starting_price():
    copy = build.load_copy()
    for app in build.load_apps():
        assert copy[app["id"]]["price_from"].startswith("$"), app["id"]


# --- Our Farm Apps: each app on a computer and a phone --------------------------------------------

def test_every_app_has_its_computer_and_phone_pictures_and_words_for_them():
    copy = build.load_copy()
    for app in build.load_apps():
        for kind in ("computer", "phone"):
            assert (build.SHOTS / f'{app["id"]}-{kind}.jpg').exists(), (app["id"], kind)
        assert len(copy[app["id"]]["shot_alt"]) > 40, app["id"]
        row = build.app_shot(app, copy[app["id"]])
        assert 'class="shot showcase"' in row and f'alt="{build.e(copy[app["id"]]["shot_alt"])}"' in row


def test_an_app_without_pictures_keeps_the_placeholder(monkeypatch, tmp_path):
    monkeypatch.setattr(build, "SHOTS", tmp_path)
    assert "placeholder shot" in build.app_shot(APP, {"shot_alt": "x"})


def test_the_pictures_stay_small():
    total = sum(p.stat().st_size for p in build.SHOTS.glob("*.jpg"))
    assert total < 900_000  # about 0.6 MB for four apps today


# --- Open, and one way in (2026-10-05) --------------------------------------------------------------

def links(tile):
    import re
    return re.findall(r'<a [^>]*href="([^"]+)"[^>]*>(?:(?!</a>).)*?</a>', tile, re.S)


def test_a_tile_opens_the_app_and_its_words_lead_to_its_page():
    """Scott, 2026-10-05, asked for links at the bottom of each card. A link can't sit inside a link, so the
    tile is no longer one big link: the name and question go to the app's page on this site, Open to the app."""
    tile = build.app_tile(APP, COPY, week())
    assert '<a class="tile' not in tile.split("tile-body")[0] and tile.lstrip().startswith('<div class="tile tile-app">')
    assert links(tile) == ["grazing-planner.html", APP["url"]]
    # Four tiles each have an Open button: a screen reader hears which app each one opens.
    assert f'<a class="btn small" href="{APP["url"]}" aria-label="Open {APP["name"]}">Open</a>' in tile
    assert tile.count("<a ") == tile.count("</a>") == 2


def test_an_app_with_sign_up_links_gets_one_on_its_tile_and_never_a_subscribe_link():
    """ "Just Open and Try for Free" (Scott). While the app is invite-only the same link reads Join the
    Waitlist; it is hidden in a browser that has used the app (member.js)."""
    for state, word, card in (("waitlist", "Join the Waitlist", "#waitlist"), ("open", "Try for Free", "#signup")):
        tile = build.app_tile(APP, {**COPY, "signup": state}, week())
        assert f'<a class="tile-link visitor-only" data-app="{APP["id"]}" href="{APP["url"]}{card}">{word}</a>' in tile
        assert links(tile) == ["grazing-planner.html", APP["url"], APP["url"] + card]
        assert "Subscribe" not in tile and "Free to try" not in tile


def test_an_app_with_no_sign_up_says_what_is_true_of_it_instead():
    tile = build.app_tile(APP, {**COPY, "tile_note": "Free, no sign-in"}, week())
    assert '<span class="tile-price">Free, no sign-in</span>' in tile and "tile-link" not in tile


def test_the_real_tiles_each_have_open_and_a_way_in_or_a_note():
    copy = build.load_copy()
    for app in build.load_apps():
        tile = build.app_tile(app, copy[app["id"]], week())
        if not app["url"]:
            continue
        assert ("tile-link" in tile) == ("signup" in copy[app["id"]]), app["id"]
        assert ("tile-link" in tile) or build.e(copy[app["id"]]["tile_note"]) in tile, app["id"]
