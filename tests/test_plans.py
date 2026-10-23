"""Free and Subscription (plans.html, 2026-10-22). Scott chose B of notes/suite-plans-B-desk-2026-10-22.png: a card per
app, what's free and what a subscription adds, with no prices until billing is built."""

import re
from html import unescape
from pathlib import Path

import pytest

import build
from test_site import site  # noqa: F401  (builds the site once, into a temporary folder)

ROOT = Path(__file__).resolve().parents[1]


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_every_live_app_has_a_card_and_my_farm_has_one(site):
    page = text(site / "plans.html")
    for app in build.load_apps():
        assert f'id="plan-{app["id"]}"' in page, app["id"]
        assert f'>{app["name"]}</h2>' in page
    assert 'id="plan-my-farm"' in page and "Your company logo on your reports and your My Farm home page" in page
    assert "<h1>What&rsquo;s Free, and What a Subscription Adds</h1>" in page


def test_no_prices_and_no_subscribe_button(site):
    page = text(site / "plans.html")
    main = page[page.index("<main"):page.index("</main>")]
    assert not re.search(r"\$\s?\d", main), "no amounts until billing is built (decided 2026-10-22)"
    assert ">Subscribe<" not in main                       # Sign Up makes a free account; Subscribe waits for a pay page


def test_only_what_exists_is_under_a_subscription():
    """An app with nothing paid yet shows what's coming (marked Coming) or that every tool is free; never a tick."""
    plans = build.load_plans()
    for p in plans["apps"]:
        assert sum(bool(p.get(k)) for k in ("paid", "coming", "none")) == 1, p["id"]
        assert p["free"], p["id"]


def test_the_apps_cards_and_this_page_list_the_same_things():
    """Herd Planner's and the Grazing Planner's Two Ways cards and this page say the same thing, row for row (when the
    apps sit beside this project, as on Scott's computer)."""
    checked = 0
    for p in build.load_plans()["apps"]:
        card = ROOT.parent / p["card"] if p.get("card") else None
        if card is None or not card.exists():
            continue
        html = text(card)
        table = html[html.index('class="plans-table"'):html.index("</table>", html.index('class="plans-table"'))]
        rows = re.findall(r'<th scope="row">(.*?)</th><td>(.*?)</td>', table)
        free = [unescape(r) for r, cell in rows if "Included" in cell and "Not included" not in cell]
        paid = [unescape(r) for r, cell in rows if "Not included" in cell]
        assert (free, paid) == (p["free"], p["paid"]), f'{p["id"]}: copy its Two Ways card here again'
        checked += 1
    if not checked:
        pytest.skip("Herd Planner and the Grazing Planner aren't beside this project")


def test_every_page_links_to_it_and_it_is_in_the_sitemap(site):
    for name in ("index.html", "about.html", "methods.html", "herd-planner.html", "barns.html"):
        page = text(site / name)
        assert '<a href="plans.html">Plans</a>' in page, name                                   # the footer
        assert '<a href="plans.html" data-note="Free and paid">Plans</a>' in page, name          # the main menu
    assert "plans.html" in text(site / "sitemap.xml")


def test_plans_is_in_the_main_menu_after_our_farm_apps(site):
    """Scott, 2026-10-22: "we're going to need a main menu item"; he chose A, Plans (notes/site-nav-plans-2026-10-22.png),
    right after Our Farm Apps. Not Subscribe (that waits for a pay page) and not Pricing (no amounts shown yet)."""
    page = text(site / "plans.html")
    nav = page[page.index('<nav class="site-nav'):page.index("</nav>", page.index('<nav class="site-nav'))]
    assert '<a href="plans.html" data-note="Free and paid" aria-current="page">Plans</a>' in nav
    assert (nav.index('class="mega-wrap"') < nav.index('<a href="plans.html" data-note')
            < nav.index('<a class="nav-barns" href="barns.html"'))
    assert "<title>Plans | Cornerpost Logic</title>" in page


def test_the_bar_stays_on_one_line_on_a_tablet():
    """With Plans added, How We Test (below 1,101 px) and Barn Prices (below 800 px) leave the bar on a tablet; both are in
    Our Farm Apps and the footer, and the phone's Menu keeps every item. Checked in Chromium from 601 to 1,280 px."""
    css = text(ROOT / "static" / "site.css")
    assert "@media (max-width: 1100px) and (min-width: 641px) { .site-nav > a.nav-methods { display: none; } }" in css
    assert "@media (max-width: 799px) and (min-width: 641px) { .site-nav > a.nav-barns { display: none; } }" in css
