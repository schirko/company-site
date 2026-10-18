"""How It Works as four cards on an app's page (2026-10-18; Scott liked a four-step card graphic, chose A of
notes/how-it-works-2026-10-18.png, and "Only the app pages"): The Data, The Method, The Answer, Your Decision, with a
tested result on The Answer that must come from How We Test. Herd Planner keeps its own How It Works (the ranch year,
tests/test_how_it_works.py), so it has no cards."""

import html
import re

import pytest

import build

STEPS = ["The Data", "The Method", "The Answer", "Your Decision"]


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site") / "docs"
    old, build.OUT = build.OUT, out          # a scratch build, never the real docs/
    try:
        yield build.build()
    finally:
        build.OUT = old


def methods_part(app_id):
    page = (build.TEMPLATES / "methods.html").read_text(encoding="utf-8")
    at = page.index(f'id="{app_id}"')
    nxt = re.search(r'<section[^>]* id="', page[at + 10:])
    text = page[at:at + 10 + nxt.start()] if nxt else page[at:]
    return html.unescape(re.sub(r"<[^>]+>", " ", text))


def with_cards():
    copy = build.load_copy()
    return [(a, copy[a["id"]]["how"]) for a in build.load_apps() if "how" in copy[a["id"]]]


def test_every_app_but_herd_planner_has_four_steps_in_order():
    copy = build.load_copy()
    have = {a["id"] for a, _ in with_cards()}
    assert have == {a["id"] for a in build.load_apps()} - {"herd-planner"}
    assert "how" not in copy["herd-planner"]
    for app, how in with_cards():
        assert [s["name"] for s in how["steps"]] == STEPS, app["id"]
        for step in how["steps"]:
            assert step["what"] and 2 <= len(step["items"]) <= 4, (app["id"], step["name"])


def test_every_tested_number_comes_from_how_we_test():
    for app, how in with_cards():
        numbers = re.findall(r"\d+(?:\.\d+)?", how["tested"])
        assert numbers, app["id"]                                     # a result, not an adjective
        part = methods_part(app["id"])
        for n in numbers:
            assert re.search(rf"(?<![\d.]){re.escape(n)}(?![\d])", part), (app["id"], n)


def test_the_cards_are_on_each_page_above_the_findings(site):
    for app, how in with_cards():
        page = (site / build.APP_PAGE.format(app["id"])).read_text(encoding="utf-8")
        at = page.index('<section class="how" id="how-it-works"')
        part = page[at:page.index("</section>", at)]
        assert f'<h2 id="how-h">How {build.e(app["name"])} Works</h2>' in part
        assert [part.index(f"</small> {s}</p>") for s in STEPS] == sorted(part.index(f"</small> {s}</p>") for s in STEPS)
        assert part.count('class="how-badge"') == 1 and f"Tested: {build.e(how['tested'])}" in part
        assert part.index('class="how-badge"') > part.index("</small> The Answer</p>") > 0
        assert f'href="methods.html#{app["id"]}"' in part
        if "<h2>What We Found</h2>" in page:
            assert at < page.index("<h2>What We Found</h2>")
    hp = (site / "herd-planner.html").read_text(encoding="utf-8")
    assert 'id="how-it-works"' not in hp and hp.count("How It Works</h2>") == 1


def test_the_cards_stack_on_a_phone():
    css = (build.STATIC / "site.css").read_text(encoding="utf-8")
    assert ".how-cards { list-style: none;" in css and "grid-template-columns: repeat(4, 1fr)" in css
    phone = css[css.index("@media (max-width: 640px) { .how-cards"):]
    assert "grid-template-columns: 1fr;" in phone.split("}")[0]


def test_your_decision_ends_with_the_way_in(site):
    """Scott, 2026-10-18: "should we copy the Open Yield Predictor button and put it in the Your Decision card?" The
    same button as the top of the page, once, at the foot of the last card."""
    for app, how in with_cards():
        page = (site / build.APP_PAGE.format(app["id"])).read_text(encoding="utf-8")
        at = page.index('<section class="how" id="how-it-works"')
        part = page[at:page.index("</section>", at)]
        words = how.get("go") or f'Open {app["name"]}'
        button = f'<a class="btn" href="{build.e(app["url"])}">{build.e(words)} &#8594;</a>'
        assert part.count('class="how-go"') == 1 and button in part, app["id"]
        assert part.index(button) > part.index("</small> Your Decision</p>")
    copy = build.load_copy()
    for app_id in ("corn-yield-predictor", "grazing-planner"):          # free to try: no account or no sign-in
        assert copy[app_id]["how"]["go"] == "Try It Free"
        assert "No account needed" in copy[app_id]["note"] or "No sign-in needed" in copy[app_id]["note"]
    assert "Free" not in copy["farm-equipment-planner"]["how"]["go"]   # needs a My Farm account: never "Try It Free"
