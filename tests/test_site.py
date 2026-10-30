"""The company site builds, every page carries the name from config.py, and nothing links nowhere."""

import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

import build
import config

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT.parent / "herd-planner" / "brand"   # the suite's master copies live with Herd Planner


@pytest.fixture(scope="module")
def site():
    return build.build()


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.found = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ("href", "src"):
            if attrs.get(key):
                self.found.append(attrs[key])


def all_pages():
    return [p[0] for p in build.PAGES] + [build.APP_PAGE.format(a["id"]) for a in build.load_apps()] + ["barns.html"]


def test_every_page_is_built_with_the_company_name(site):
    for name in all_pages():
        page = (site / name).read_text(encoding="utf-8")
        assert config.NAME in page, name
        assert "${" not in page, f"{name} has an unfilled placeholder"


def test_no_internal_link_is_broken(site):
    for name in all_pages():
        parser = Links()
        parser.feed((site / name).read_text(encoding="utf-8"))
        for link in parser.found:
            if re.match(r"^(https?:|mailto:|#)", link):
                continue
            target = site / link.split("#")[0].split("?")[0]  # ?v= marks a file version
            assert target.exists(), f"{name} links to {link}, which isn't in docs/"


def test_every_app_in_the_suite_list_is_on_the_home_page(site):
    home = (site / "index.html").read_text(encoding="utf-8")
    for app in json.loads((ROOT / "static/suite/suite-apps.json").read_text(encoding="utf-8"))["apps"]:
        assert app["name"] in home
        assert (site / "suite/suite-logos" / f"{app['id']}.svg").exists()
        if app["url"]:
            assert app["url"] in home


def test_search_engines_are_kept_out_while_the_name_is_a_placeholder(site):
    home = (site / "index.html").read_text(encoding="utf-8")
    if config.PUBLIC:
        assert 'name="robots"' not in home and "Sitemap:" in (site / "robots.txt").read_text(encoding="utf-8")
    else:
        assert '<meta name="robots" content="noindex">' in home
        assert "Disallow: /" in (site / "robots.txt").read_text(encoding="utf-8")


def test_no_personal_email_address_on_the_public_site(site):
    """The contact address must be a company one, set on purpose in config.py."""
    for page in site.glob("*.html"):
        for address in re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", page.read_text(encoding="utf-8")):
            assert address == config.EMAIL, f"{page.name} shows {address}"


def test_every_app_has_home_page_words():
    """content/apps.json holds the home page's longer words about each app in the suite list."""
    copy = build.load_copy()
    for app in build.load_apps():
        entry = copy.get(app["id"])
        assert entry, f"content/apps.json has no entry for {app['id']}"
        assert entry["question"] and entry["audience"] and entry["note"] and len(entry["points"]) >= 3, app["id"]


def test_how_we_test_covers_every_app(site):
    """An app added to the suite list (or renamed) needs its section on the methods page."""
    page = (site / "methods.html").read_text(encoding="utf-8")
    for app in json.loads((ROOT / "static/suite/suite-apps.json").read_text(encoding="utf-8"))["apps"]:
        assert f'id="{app["id"]}"' in page, f"methods page has no section for {app['id']}"
        assert f"<h2>{app['name']}" in page, f"methods page doesn't name {app['name']}"


def drawing(path):
    """The drawing in an SVG file. Some tools add a note about where a file came from (a <metadata> block) when they
    save it; that note isn't part of the picture, so two copies of one drawing still compare as equal."""
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").strip()
    text = re.sub(r"<metadata>.*?</metadata>", "", text, flags=re.S)
    return text.replace(' xmlns:c2pa="http://c2pa.org/manifest"', "")


def test_the_app_logos_are_the_line_symbols_on_rounded_tiles():
    """October 7, 2026: the four app logos were redrawn (a cream line symbol with one gold piece on a rounded square
    in the app's colour), after a graphic designer called the first ones clip art. This holds without Herd Planner
    beside the project. The company's own mark (static/brand, favicon.svg) is a different thing and did not change."""
    tiles = {"herd-planner": "#3f6e4e", "corn-yield-predictor": "#4a3520", "grazing-planner": "#2f5d5a", "farm-equipment-planner": "#23374d"}
    apps = json.loads((ROOT / "static/suite/suite-apps.json").read_text(encoding="utf-8"))["apps"]
    assert {a["id"] for a in apps} == set(tiles)
    for app, tile in tiles.items():
        svg = drawing(ROOT / "static/suite/suite-logos" / f"{app}.svg")
        assert f'<rect x="2" y="2" width="96" height="96" rx="22" fill="{tile}"/>' in svg, app
        assert set(re.findall(r"#[0-9a-f]{6}", svg)) == {tile, "#f4efe3", "#d9a441"}, app


@pytest.mark.skipif(not (MASTER / "herd-planner-logo-small.svg").exists(), reason="Herd Planner with the redrawn logos isn't checked out next to this project")
def test_the_app_logos_match_the_master_copies():
    for app in json.loads((ROOT / "static/suite/suite-apps.json").read_text(encoding="utf-8"))["apps"]:
        copy, master = ROOT / "static/suite/suite-logos" / f"{app['id']}.svg", MASTER / f"{app['id']}-logo.svg"
        assert drawing(copy) == drawing(master), f"{app['id']}.svg drifted from herd-planner/brand"


@pytest.mark.skipif(not MASTER.exists(), reason="Herd Planner isn't checked out next to this project")
def test_suite_files_match_the_master_copies():
    for name in ("suite.css", "suite.js", "suite-apps.json"):
        copy = (ROOT / "static/suite" / name).read_bytes().replace(b"\r\n", b"\n")
        assert copy == (MASTER / name).read_bytes().replace(b"\r\n", b"\n"), f"{name} drifted from herd-planner/brand"


def test_the_apps_link_back_to_this_site_by_its_own_name():
    """Every app's header starts with the company's name, linking here ("company" in suite-apps.json).
    When the company is named, change config.py AND herd-planner/brand/suite-apps.json, then copy it out."""
    company = json.loads((ROOT / "static/suite/suite-apps.json").read_text(encoding="utf-8"))["company"]
    assert company["name"] == config.NAME
    assert company["url"] == config.SITE_URL


def site_nav(page):
    return page[page.index('<nav class="site-nav'):page.index("</nav>")]


def test_sign_in_is_in_every_page_menu(site):
    """Sign In goes to My Farm on every page (2026-10-18: one sign-in for every app; before, on the page of an app
    with sign-up links it went to that app's own sign-in card)."""
    copy = build.load_copy()
    own = {build.APP_PAGE.format(a["id"]): build.signup(a, copy[a["id"]]) for a in build.load_apps()}
    for name in all_pages():
        nav = site_nav((site / name).read_text(encoding="utf-8"))
        where = config.ACCOUNT_URL
        assert f'href="{where}">Sign In</a>' in nav and nav.count(">Sign In</a>") == 1, name
        assert "<summary>Our Farm Apps</summary>" in nav, name


def test_apps_in_development_get_an_honest_tile_and_nothing_else(site):
    """A tile on the home page (tag, Get Notified), but no app page and no footer link. Scott, 2026-10-12: a fifth
    tile, "Coming Soon", not clickable itself, \"just makes the suite look stronger\". Since suite version 10
    (2026-10-14) it is also a greyed Coming Soon row in the Our Farm Apps menu (test_the_menu_shows_coming_soon_apps)."""
    copy = json.loads((ROOT / "content/apps.json").read_text(encoding="utf-8"))
    suite_ids = {a["id"] for a in build.load_apps()}
    home = (site / "index.html").read_text(encoding="utf-8")
    for app in copy["in_development"]:
        assert app["id"] not in suite_ids, f"{app['id']} is live: remove it from in_development"
        assert (site / "soon" / f"{app['id']}.svg").exists()
        tile = home[home.index(f'soon/{app["id"]}.svg', home.index("<main")):]   # the tile, not the menu's row
        tile = tile[:tile.index("</div>")]
        assert "Coming Soon" in tile and 'href="#notify"' in tile and html.escape(app["name"]) in tile and "Get Notified" in tile
        assert not (site / build.APP_PAGE.format(app["id"])).exists()
    assert 'id="notify"' in home
    assert len(re.findall(r'class="tile[ "]', home)) == len(suite_ids) + len(copy["in_development"])


def test_apps_in_development_get_a_slim_strip_at_the_foot_of_our_farm_apps(site):
    """Scott, 2026-10-13, option B of notes/hay-row-A-or-B-2026-10-13.png: below the apps that are built, a dashed
    strip with the question, the Coming Soon tag and Get Notified. Smaller than a built app's row on purpose: no
    points, no screenshot, no Open button and no page link."""
    copy = json.loads((ROOT / "content/apps.json").read_text(encoding="utf-8"))
    home = (site / "index.html").read_text(encoding="utf-8")
    section = home[home.index('id="our-apps"'):]
    section = section[:section.index("</section>")]
    last_row = max(section.index(f'id="{a["id"]}"') for a in build.load_apps())
    for app in copy["in_development"]:
        strip = section[section.index(f'<div class="dev-strip" id="{app["id"]}">'):]
        strip = strip[:strip.index("</a>\n    </div>")]
        assert section.index(f'<div class="dev-strip" id="{app["id"]}">') > last_row       # after every built app
        for words in ("Coming Soon", html.escape(app["name"]), html.escape(app["question"]), 'href="#notify"', "Get Notified"):
            assert words in strip, words
        assert "Open " not in strip and ".html" not in strip and "app-row" not in strip
    assert section.count('class="dev-strip"') == len(copy["in_development"])


def test_every_page_has_the_phone_bar_and_menu(site):
    """Scott, 2026-10-13: one phone header for every app and the site, Herd Planner's (herd-planner/notes/
    phone-headers-now-and-proposed-2026-10-13.png, "As drawn"; Sign In "On the bar"; tablets "Keep the row").
    Below 640 px: the logo, Sign In (or a returning browser's Open link) and Menu; Menu opens the header's links as
    a white list with a grey note on each. Checked in Chromium at 360 and 390 px (and 768 and 1280: unchanged)."""
    for name in all_pages():
        page = (site / name).read_text(encoding="utf-8")
        head = page[page.index("<header"):page.index("</header>")]
        bar = head.index(f'<div class="bar-account"><a class="nav-signin" href="{config.ACCOUNT_URL}">Sign In</a>')
        menu = head.index('<button type="button" class="menu-btn" id="menu-btn" aria-expanded="false" aria-controls="site-nav">')
        assert bar < menu < head.index('id="site-nav"'), name
        for note, words in (("Every barn", "Barn Prices"), ("Who we are", "About"), ("How we check it", "How We Test")):
            assert re.search(rf'data-note="{note}"[^>]*>{words}</a>', head), (name, words)
        assert head.count(">Sign In</a>") == 2, name                  # the bar's and the menu's (shown one at a time)
    styles = (ROOT / "static/site.css").read_text(encoding="utf-8")
    phone = styles[styles.index(".menu-btn, .bar-account { display: none; }"):]
    assert "@media (max-width: 640px)" in phone and ".site-header.menu-open .site-nav { display: flex;" in phone
    assert "nav-visitor" not in phone                                  # 2026-10-18: Sign In never hides
    js = (ROOT / "static/menu.js").read_text(encoding="utf-8")
    assert 'matchMedia("(max-width: 640px)")' in js and "if (flat) { setMenu(false); btn.focus(); return; }" in js


def test_the_location_is_centennial(site):
    assert config.LOCATION == "Centennial, Colorado"
    assert "Built in Centennial, Colorado" in (site / "index.html").read_text(encoding="utf-8")


def test_styles_and_scripts_get_a_new_address_when_they_change(site):
    """A browser that kept last week's site.css would draw new pages with old styles."""
    import hashlib

    for page in ("index.html", "barns.html"):
        text = (site / page).read_text(encoding="utf-8")
        for name in ("suite/suite.css", "site.css", "suite/suite.js"):
            tag = hashlib.sha256((build.STATIC / name).read_bytes()).hexdigest()[:10]
            assert f'"{name}?v={tag}"' in text, (page, name)
    assert '"slider.js?v=' in (site / "index.html").read_text(encoding="utf-8")


def test_the_custom_domain_survives_every_build(site):
    """GitHub Pages serves cornerpostlogic.com only while docs/CNAME names it; build.py empties docs/ each time."""
    import config

    assert (site / "CNAME").read_text(encoding="utf-8").strip() == config.DOMAIN
    assert config.SITE_URL == f"https://{config.DOMAIN}/"
    home = (site / "index.html").read_text(encoding="utf-8")
    assert f'<link rel="canonical" href="https://{config.DOMAIN}/">' in home
    if config.PUBLIC:
        assert "noindex" not in home
        assert f"Sitemap: https://{config.DOMAIN}/sitemap.xml" in (site / "robots.txt").read_text(encoding="utf-8")


def test_every_page_shows_the_logo_with_the_company_name_as_its_text(site):
    """The logo is a picture of the name, so its alt text must be the name (screen readers, search, a failed load)."""
    for name in all_pages():
        page = (site / name).read_text(encoding="utf-8")
        assert f'<img src="brand/wordmark-dark.svg" alt="{config.NAME}"' in page, name
        assert '<link rel="apple-touch-icon" href="brand/icon-180.png">' in page, name
    for f in ("wordmark-dark.svg", "wordmark-light.svg", "icon.svg", "icon-180.png", "icon-512.png"):
        assert (site / "brand" / f).exists(), f
    # Same drawing (a file-provenance <metadata> block, if a tool added one, may differ).
    drawing = lambda f: re.sub(r"<metadata>.*?</metadata>", "", (site / f).read_text(encoding="utf-8"), flags=re.S)
    assert drawing("favicon.svg") == drawing("brand/icon.svg")


def test_the_farm_apps_menu_sorts_every_app_by_operation(site):
    """The header's Our Farm Apps menu (option C, 2026-09-30): each live app in exactly one group, linking to its
    page with its logo and one line; then the free tools, How We Test and Your Account."""
    grouped = [i for _, _, ids in build.OPERATIONS for i in ids]
    live = {a["id"]: a for a in build.load_apps()}
    assert sorted(grouped) == sorted(live), "every live app needs one line in build.OPERATIONS"
    page = (site / "index.html").read_text(encoding="utf-8")
    menu = page[page.index("<details class=\"mega\""):page.index("</details>", page.index("<details class=\"mega\""))]
    for app_id, app in live.items():
        assert f'href="{build.APP_PAGE.format(app_id)}"' in menu and build.e(app["name"]) in menu and build.e(app["what"]) in menu
        assert f'suite-logos/{app_id}.svg' in menu
    for href in ('href="barns.html"', 'href="index.html#this-week"', 'href="methods.html"', f'href="{config.ACCOUNT_URL}"'):
        assert href in menu, href
    assert 'id="this-week"' in page   # the county panel the menu points at
    assert 'src="menu.js?v=' in page


def test_each_menu_group_opens_with_a_green_band(site):
    """Scott, 2026-10-07: "For Ranches" and "For Farms" "don't seem to stand out". Each group's heading and lead
    sit on one slim band in the header's green; the lead's light green must stay readable on it."""
    page = (site / "index.html").read_text(encoding="utf-8")
    for title, lead, _ids in build.OPERATIONS:
        assert (f'<div class="mega-op-head"><p class="mega-op-title">{build.e(title)}</p>'
                f'<p class="mega-op-lead">{build.e(lead)}</p></div>') in page
    css = (ROOT / "static" / "site.css").read_text(encoding="utf-8")
    head = css[css.index(".mega-op-head {"):]
    assert "background: var(--suite-deep-green)" in head[:head.index("}")]

    def lum(hexcolor):
        rgb = [int(hexcolor[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    lead = css[css.index(".mega-op-lead {"):]
    color = lead[lead.index("color: #") + 7:lead.index("color: #") + 14]
    ratio = (lum(color) + 0.05) / (lum("#243b2f") + 0.05)
    assert ratio >= 4.5, f"the lead {color} on the band is {ratio:.1f} to 1; small text needs 4.5"


def test_an_app_page_marks_the_menu_as_where_you_are(site):
    page = (site / build.APP_PAGE.format("herd-planner")).read_text(encoding="utf-8")
    assert '<div class="mega-wrap" data-current>' in page
    assert '<div class="mega-wrap" data-current>' not in (site / "about.html").read_text(encoding="utf-8")


# --- the photo behind the home page's headline ---------------------------------------------------


def test_the_home_page_photo_carries_its_credit_line(site):
    page = (site / "index.html").read_text(encoding="utf-8")
    hero = page[page.index('<section class="hero'):page.index("</section>", page.index('<section class="hero'))]
    address = re.search(r'background-image: url\((photos/[\w.-]+)\?v=[0-9a-f]{10}\)', hero)
    assert address and (site / address.group(1)).exists()
    assert f'<p class="photo-credit">{config.HERO_CREDIT}</p>' in hero and config.HERO_CREDIT.strip()
    # Sized for the web: a phone on a slow connection still gets the headline quickly.
    assert (site / address.group(1)).stat().st_size < 450_000


def test_a_photo_without_a_credit_line_stops_the_build(monkeypatch):
    monkeypatch.setattr(config, "HERO_CREDIT", "  ")
    with pytest.raises(SystemExit, match="credit"):
        build.hero_photo()


def test_the_home_page_works_with_no_photo(monkeypatch):
    monkeypatch.setattr(config, "HERO_PHOTO", "")
    assert build.hero_photo() == ("", "", "")
    monkeypatch.setattr(config, "HERO_PHOTO", "photos/not-there.jpg")   # named but not downloaded yet
    assert build.hero_photo() == ("", "", "")


def test_the_headline_and_this_weeks_numbers_sit_on_the_photo_and_the_panel_follows(site):
    page = (site / "index.html").read_text(encoding="utf-8")
    hero_at, week_at, tiles_at = (page.index(mark) for mark in ('<section class="hero', '<section class="week"', '<section class="tiles-band"'))
    assert hero_at < page.index("<h1>") < page.index('id="pins"') < week_at < page.index('id="this-week"') < tiles_at
    assert page.count("<h1>") == 1


def test_the_proof_figures_read_in_plain_words_and_lead_to_how_we_test(site):
    """Scott, October 3, 2026: "typical miss pricing calves at 26 sales the model never saw" was not plain
    (he could not follow it, so a rancher won't). The figure is said as a gap from the real sale price, with
    what it comes to in dollars, and each of the three figures links to the section that explains it."""
    home = (site / "index.html").read_text(encoding="utf-8")
    proof = home[home.index('class="proof-stats'):home.index('<div class="stories">')]   # in "Answers You Can Check" since 2026-10-08
    assert "typical miss" not in proof and "never saw" not in proof
    assert "typical gap between our calf price estimate and the real sale price: about $60 on a $2,500 calf" in proof
    assert "26 auctions the model had not seen" in proof
    # Scott, October 10, 2026: "0.51 score (1.0 is perfect)" and "rows of Iowa State's field capacity table" meant
    # nothing to a farmer. Bushels an acre and machine sizes instead (crop-yield-predictor README section 5).
    assert "<strong>0.51</strong>" not in proof and "1.0 is perfect" not in proof and "rows of" not in proof
    assert "<strong>15 bu</strong><span>an acre: typical gap between our estimate and an Iowa county" in proof
    assert "machine sizes, from combines to sprayers" in proof
    methods = (site / "methods.html").read_text(encoding="utf-8")
    for section in ("herd-planner", "corn-yield-predictor", "farm-equipment-planner"):
        assert f'<a href="methods.html#{section}"><span class="proof-app"><img src="suite/suite-logos/{section}.svg"' in proof
        assert f'id="{section}"' in methods                       # the link lands somewhere
    assert 62.5 == 2500 * 0.025                                   # "about $60": 2.5% of a $2,500 calf


def test_why_use_our_apps_leads_to_how_we_test(site):
    """The sentence promises each finding's source and limits; the link is where that promise is kept. Each
    finding also links to its own app's section."""
    home = (site / "index.html").read_text(encoding="utf-8")
    why = home[home.index('<section class="why" id="why">'):]
    lede = why[:why.index('<div class="stories">')]
    assert "where its numbers came from and where it can be wrong" in " ".join(lede.split())
    assert '<a href="methods.html">How we test them</a>' in lede
    stories = json.loads((ROOT / "content/stories.json").read_text(encoding="utf-8"))["stories"]
    methods = (site / "methods.html").read_text(encoding="utf-8")
    for story in stories:
        if f'id="{story["id"]}"' in why:                          # the ones shown on the home page
            assert f'<a href="methods.html#{story["app"]}">How we test it</a>' in why, story["id"]
            assert f'id="{story["app"]}"' in methods, story["app"]


def test_the_header_logo_is_the_size_scott_picked():
    """October 3, 2026: on a computer the logo "seemed to be hiding" at 36 px. From sheets of three sizes Scott
    picked 52 px for a computer and kept 30 px for a phone. Windows in between keep 36 px, so the name and the
    menu share a line as they did before."""
    css = (ROOT / "static/site.css").read_text(encoding="utf-8")
    assert ".wordmark img { display: block; height: 52px; width: auto; }" in css
    assert "@media (max-width: 959px) { .wordmark img { height: 36px; } }" in css
    phone = css.index(".wordmark img { height: 30px; }")
    assert "@media (max-width: 600px) {" in css[phone - 250:phone]              # the phone size sits in the phone rule...
    assert css.index("max-width: 959px") < phone                                # ...which comes last, so it wins
    layout = (ROOT / "templates/layout.html").read_text(encoding="utf-8")
    assert 'width="338" height="52"' in layout                     # the shape the browser saves room for: 796.2 x 122.4 scaled
    assert round(52 * 796.2 / 122.4) == 338


# --- the fuller app page (layout A, chosen 2026-10-05): templates/app_full.html --------------------------------

FULL = [a for a in build.load_apps() if "page" in build.load_copy()[a["id"]]]


def full_part(page):
    """The fuller page's own parts: from the headline down to where the weekly card begins."""
    return page[page.index('<div class="lp-hero">'):page.index('lp-weekly')]


def words(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def test_herd_planner_has_the_fuller_page():
    assert "herd-planner" in [a["id"] for a in FULL]


@pytest.mark.parametrize("app", FULL, ids=lambda a: a["id"])
def test_the_fuller_page_runs_headline_sample_what_you_get_steps_then_this_week(site, app):
    copy = build.load_copy()[app["id"]]
    page = (site / build.APP_PAGE.format(app["id"])).read_text(encoding="utf-8")
    assert page.count("<h1>") == 1 and f'<h1>{build.e(copy["page"]["headline"])}</h1>' in page
    assert f'<p class="lp-name">{build.e(app["name"])}</p>' in page          # the app is still named, above the headline
    sample = copy["page"]["sample"]
    order = [page.index(mark) for mark in ("<h1>", f'id="{sample["id"]}"', 'id="what-you-get"', 'id="how-it-works"',
                                           "lp-weekly", '<h2 class="found-h">What We Found</h2>', "<h2>Where the Number Comes From</h2>")]
    assert order == sorted(order)
    # Two buttons: the way in for someone new (or, for a browser that has used the app, straight into it), and
    # down to the sample (a link on this page, which the link test follows).
    su = build.signup(app, copy)
    top = page[page.index('<p class="lp-cta">'):page.index('</p>', page.index('<p class="lp-cta">'))]
    assert f'<a class="btn visitor-only" data-app="{app["id"]}" href="{su["url"]}">{su["button"]}</a>' in top
    assert f'<a class="btn member-only" data-app="{app["id"]}" href="{build.e(app["url"])}">Open {build.e(app["name"])}</a>' in top
    assert f'<a class="btn ghost" href="#{sample["id"]}">{build.e(sample["button"])}</a>' in top
    order = [page.index(mark) for mark in ('id="what-you-get"', 'id="year"', 'id="how-it-works"')]
    assert order == sorted(order)
    # 2026-10-18: the four How It Works cards took the five-season strip's place (Scott chose B).
    assert "steps" not in copy["page"] and page.count('<li class="how-card">') == 4


@pytest.mark.parametrize("app", FULL, ids=lambda a: a["id"])
def test_the_sample_is_a_real_picture_cut_off_and_says_what_it_is(site, app):
    """Scott: "Showing cutoff lending reports is something helpful in getting customers." The pricing plan's rule:
    say what a subscriber would see next to the free number, never a blurred fake result. So the sample is a real
    page from the app with made-up cattle, it is cut off by the page's styles (not blurred), and its caption says
    the cattle are made up and that the report is not an appraisal."""
    sample = build.load_copy()[app["id"]]["page"]["sample"]
    picture = site / sample["image"]
    assert picture.exists() and picture.stat().st_size < 150_000
    assert len(sample["alt"]) > 60 and "made-up" in sample["alt"]
    assert "made-up cattle" in sample["caption"] and "not an appraisal" in sample["caption"]
    page = (site / build.APP_PAGE.format(app["id"])).read_text(encoding="utf-8")
    assert f'alt="{build.e(sample["alt"])}"' in page and build.e(sample["more"]) in page
    styles = (site / "site.css").read_text(encoding="utf-8")
    cut = styles[styles.index(".lp-paper {"):]
    assert "overflow: hidden" in cut[:cut.index("}")] and "max-height" in cut[:cut.index("}")]
    assert "blur(" not in styles


@pytest.mark.parametrize("app", FULL, ids=lambda a: a["id"])
def test_the_fuller_page_shows_no_price_and_calls_the_paid_level_a_subscription(site, app):
    """No price until billing exists (config.SHOW_PRICES is False: the pilot shows none). And the paid level is a
    subscription, never "the plan", Pro, Premium or an upgrade (Scott, 2026-10-04)."""
    part = words(full_part((site / build.APP_PAGE.format(app["id"])).read_text(encoding="utf-8")))
    assert not config.SHOW_PRICES
    assert "$" not in part and "/mo" not in part and "a month" not in part
    assert "With a Subscription" in part and "first 30 days" in part
    assert not re.search(r"\b(the|a|no|your) plans?\b(?! that)", part.replace("herd growth plan", ""), re.I), part
    for word in ("Pro ", "Premium", "pgrade"):
        assert word not in part


@pytest.mark.parametrize("app", FULL, ids=lambda a: a["id"])
def test_free_and_subscription_are_two_different_lists(app):
    page = build.load_copy()[app["id"]]["page"]
    assert len(page["free"]) >= 4 and len(page["subscription"]) >= 4
    assert not set(page["free"]) & set(page["subscription"])
    assert len(page["trial"]) == 2


def test_a_missing_sample_picture_stops_the_build():
    app = FULL[0]
    copy = json.loads(json.dumps(build.load_copy()[app["id"]]))
    copy["page"]["sample"]["image"] = "shots/not-there.png"
    with pytest.raises(SystemExit, match="not-there.png"):
        build.full_page_values(app, copy)


def test_apps_without_a_page_block_keep_the_shorter_page(site):
    copy = build.load_copy()
    for app in build.load_apps():
        if "page" in copy[app["id"]]:
            continue
        page = (site / build.APP_PAGE.format(app["id"])).read_text(encoding="utf-8")
        assert 'class="lp-' not in page and "<h2>What It Does</h2>" in page and f'<h1>{build.e(app["name"])}</h1>' in page


@pytest.mark.skipif(not MASTER.exists(), reason="Herd Planner isn't checked out next to this project")
def test_herd_planners_page_opens_with_the_apps_own_headline():
    """Scott, 2026-10-05, of the app's welcome ("Know what your cattle are worth: what to sell, what to keep"):
    "I like that." So this site's Herd Planner page opens with the same words as the app a visitor lands in
    next. If the app's headline changes, change "headline" in content/apps.json to match."""
    welcome = (MASTER.parent / "src" / "herd_planner" / "web" / "index.html").read_text(encoding="utf-8")
    headline = build.load_copy()["herd-planner"]["page"]["headline"]
    assert f">{build.e(headline)}<" in welcome




# --- Two pages side by side: the lender's report and the buyer's sale sheet (2026-10-05) -------------
# Scott asked whether the app should do more with health records and whether sale barns need a printout like
# the lender's. It already has one (the calf sale sheet and health record, free); the page never said so.
# He chose "both pages side by side in one band" from three mockups.

PAIRED = [a for a in FULL if build.load_copy()[a["id"]]["page"].get("second_sample")]


def test_herd_planner_shows_the_buyers_sheet_beside_the_lenders_report():
    assert "herd-planner" in [a["id"] for a in PAIRED]


@pytest.mark.parametrize("app", PAIRED, ids=lambda a: a["id"])
def test_both_pages_sit_in_one_band_each_under_its_own_level(site, app):
    page_words = build.load_copy()[app["id"]]["page"]
    first, second = page_words["sample"], page_words["second_sample"]
    page = (site / build.APP_PAGE.format(app["id"])).read_text(encoding="utf-8")
    band = page[page.index(f'<div class="lp-band" id="{first["id"]}">'):page.index('id="what-you-get"')]
    assert f'<h2>{build.e(page_words["samples_title"])}</h2>' in band and band.count('<div class="lp-half"') == 2
    halves = band.split('<div class="lp-half"')[1:]
    for half, smp, tag in zip(halves, (first, second), ('<span class="lp-tag">', '<span class="lp-tag lp-tag-free">')):
        assert f'{tag}{build.e(smp["tag"])}</span>' in half and f'<h3>{build.e(smp["title"])}</h3>' in half
        assert f'src="{smp["image"]}"' in half and build.e(smp["more"]) in half and build.e(smp["caption"]) in half
    assert first["tag"] == "With a subscription" and second["tag"] == "Free"
    # The button under the headline still lands on the band, and the sign-up line still closes it.
    assert f'href="#{first["id"]}"' in page and band.count('class="lp-ask visitor-only"') == 1
    assert "$" not in words(band)


@pytest.mark.parametrize("app", PAIRED, ids=lambda a: a["id"])
def test_the_second_sample_keeps_the_first_ones_rules(site, app):
    """A real page from the app with made-up cattle, marked as such on the page itself and in its caption, cut
    off by the styles and never blurred; and it claims no more for the page than the app does (the sale sheet
    prints the seller's own records, which Herd Planner has not checked)."""
    second = build.load_copy()[app["id"]]["page"]["second_sample"]
    picture = site / second["image"]
    assert picture.exists() and picture.stat().st_size < 150_000
    assert len(second["alt"]) > 60 and "made-up" in second["alt"] and "marked as a demo" in second["alt"]
    assert "made-up cattle" in second["caption"] and "does not check" in second["caption"]
    styles = (site / "site.css").read_text(encoding="utf-8")
    assert "blur(" not in styles and ".lp-pair .lp-paper { height:" in styles
    assert ".lp-paper {" in styles and "overflow: hidden" in styles[styles.index(".lp-paper {"):styles.index(".lp-paper {") + 400]


@pytest.mark.parametrize("app", PAIRED, ids=lambda a: a["id"])
def test_a_free_page_is_in_the_free_list_and_never_in_the_subscription_list(app):
    page_words = build.load_copy()[app["id"]]["page"]
    assert page_words["second_sample"]["tag"] == "Free"
    assert any("sale sheet" in line.lower() for line in page_words["free"])
    assert not any("sale sheet" in line.lower() for line in page_words["subscription"])
    fall = next(s for s in page_words["year"]["seasons"] if s["id"] == "fall")
    assert "sale sheet" in fall["text"] and "always free" in fall["text"]


def test_a_missing_second_picture_stops_the_build():
    app = PAIRED[0]
    copy = json.loads(json.dumps(build.load_copy()[app["id"]]))
    copy["page"]["second_sample"]["image"] = "shots/not-there-either.png"
    with pytest.raises(SystemExit, match="not-there-either.png"):
        build.full_page_values(app, copy, "2026-10-02")


def test_without_a_second_sample_the_band_is_as_it_was():
    """Another app's page, or this one with the second sample taken out, keeps the one sample with its points."""
    app = PAIRED[0]
    copy = json.loads(json.dumps(build.load_copy()[app["id"]]))
    del copy["page"]["second_sample"]
    band = build.full_page_values(app, copy, "2026-10-02")["sample_band"]
    assert "lp-pair" not in band and '<div class="lp-band-top">' in band
    assert all(build.e(point) in band for point in copy["page"]["sample"]["points"])


# --- Sign-up links (2026-10-05) --------------------------------------------------------------------
# Scott: "I think we need to be subtly aggressive in having subscribe/sign up links to the products,
# especially if they are on a product home page." One setting per app ("signup" in content/apps.json) words
# every link; the words mean two different things and are never mixed: Sign Up / Try for Free makes a free
# account, Subscribe pays (so it waits for a pay page).
#
# These tests read what the build writes. How the pages behave in a browser (the remembered browser, Forget
# this, the header at every width, the links landing on the app's cards) is checked by
# herd-planner/tests/browser/site_links.js, which drives this site and the app together.

SIGNED = [a for a in build.load_apps() if build.signup(a, build.load_copy()[a["id"]])]
VOID = {"img", "br", "meta", "link", "input", "hr", "source", "path", "rect", "circle", "line", "polyline", "polygon", "ellipse", "use", "stop"}


class Guards(HTMLParser):
    """Every link and button on a page, with its words and whether it, or anything around it, is marked for new
    visitors only (visitor-only) or for a browser that has used the app (member-only)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.found, self.open = [], [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = (attrs.get("class") or "").split()
        kind = next((k for k in ("visitor-only", "member-only") if k in classes), None)
        if tag in ("a", "button"):
            around = kind or next((k for k in reversed(self.stack) if k), None)
            self.open.append({"tag": tag, "href": attrs.get("href"), "for": around, "text": "", "depth": len(self.stack)})
        if tag not in VOID:
            self.stack.append(kind)

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_data(self, data):
        for item in self.open:
            item["text"] += data

    def handle_endtag(self, tag):
        if tag in VOID or not self.stack:
            return
        self.stack.pop()
        if tag in ("a", "button") and self.open:
            item = self.open.pop()
            item["text"] = re.sub(r"\s+", " ", item["text"]).strip()
            self.found.append(item)


def controls(html):
    parser = Guards()
    parser.feed(html)
    return parser.found


def with_state(app, state):
    copy = json.loads(json.dumps(build.load_copy()[app["id"]]))
    copy["signup"] = state
    return copy


def test_herd_planner_is_on_the_waitlist_and_has_sign_up_links():
    """Herd Planner online is invite-only (Scott, 2026-10-05: "the waitlist does make sense"). The day its own
    sign-up setting changes on Render, "signup" in content/apps.json changes to "open" the same day."""
    copy = build.load_copy()["herd-planner"]
    assert copy["signup"] == "waitlist" and "herd-planner" in [a["id"] for a in SIGNED]


def test_every_app_says_how_a_new_person_gets_in():
    copy = build.load_copy()
    for app in build.load_apps():
        entry = copy[app["id"]]
        assert ("signup" in entry) != ("tile_note" in entry), app["id"]   # one or the other, never neither


def test_a_setting_or_an_address_the_site_cannot_use_stops_the_build():
    app = SIGNED[0]
    with pytest.raises(SystemExit, match="signup"):
        build.signup(app, {"signup": "soon"})
    with pytest.raises(SystemExit, match="plain"):
        build.signup({**app, "url": app["url"] + "?from=site"}, {"signup": "open"})
    assert build.signup(app, {}) is None and build.signup({**app, "url": None}, {"signup": "open"}) is None
    su = build.signup({**app, "url": "https://example.test/app"}, {"signup": "waitlist"})   # with or without the slash
    assert su["url"] == "https://example.test/app/#waitlist" and su["signin"] == "https://example.test/app/#signin"


@pytest.mark.parametrize("state, button, card, others, wrong", [
    ("waitlist", "Join the Waitlist", "#waitlist", {""}, "Sign Up"),
    ("open", "Sign Up Free", "#signup", {"", "#signin"}, "Waitlist")])
def test_one_setting_words_every_sign_up_link_on_the_page(state, button, card, others, wrong):
    """Each state says only what is true of it: on the waitlist nothing offers to sign up, and with sign-up
    open nothing mentions a waitlist. Every link opens the app on the card it names. "Have an invite or an
    account?" leads to the whole first screen (an invite needs the account form, an account the sign-in card);
    "Already have an account?" to the sign-in card."""
    app = SIGNED[0]
    copy = with_state(app, state)
    v = build.full_page_values(app, copy, "2026-10-02")
    spots = ("open_button", "fine", "sample_band", "free_band", "shot", "closing")
    parts = " ".join(v[k] for k in spots)
    assert wrong not in words(parts), state
    base = app["url"].rstrip("/") + "/"
    hrefs = set(re.findall(r'href="(%s[^"]*)"' % re.escape(base), parts))
    assert hrefs == {base + card} | {base + o for o in others}
    for where in ("open_button", "sample_band", "free_band", "shot", "closing"):   # every spot Scott kept
        ways_in = [c for c in controls(v[where]) if c["href"] == base + card]
        assert ways_in, (state, where)
        assert all(c["for"] == "visitor-only" for c in ways_in), (state, where)   # gone once the browser uses the app
    assert sum(c["text"] == button for c in controls(parts)) >= 4
    assert "$" not in words(parts)   # still no price
    nav = controls(build.nav_account(build.load_apps(), {**build.load_copy(), app["id"]: copy}, app))
    # Sign In: My Farm. Since 2026-10-20 also the hidden menu under your name (account.js): My Farm, Sign Out (a button)
    assert [(c["href"], c["for"]) for c in nav] == [(config.ACCOUNT_URL, None), (build.MY_FARM_HOME, None), (None, None),
                                                       (base + card, "visitor-only")]


def test_on_the_waitlist_nothing_beside_a_button_promises_what_only_an_account_gives():
    """Joining a waitlist starts no 30 days and shows nobody their cattle's worth this week. So beside the
    waitlist button the 30 days are "With an account", and the closing headline asks rather than offers."""
    app = SIGNED[0]
    page = build.load_copy()[app["id"]]["page"]
    waiting, opened = page["signup"]["waitlist"], page["signup"]["open"]
    assert waiting["trial_lead"].startswith("With an account") and "30 days" in waiting["trial_lead"]
    assert waiting["fine"].count("With an account") == 1
    for promise in ("this week", "today", "now", "worth"):
        assert promise not in waiting["close_title"].lower()
    band = build.full_page_values(app, with_state(app, "waitlist"), "2026-10-02")["free_band"]
    assert f'<strong>{build.e(waiting["trial_lead"])}</strong>' in band and f'<strong>{build.e(page["trial"][0])}</strong>' not in band
    band = build.full_page_values(app, with_state(app, "open"), "2026-10-02")["free_band"]
    assert f'<strong>{build.e(page["trial"][0])}</strong>' in band and "trial_lead" not in opened


def test_what_you_get_has_a_button_under_each_list_only_when_sign_up_is_open():
    app = SIGNED[0]
    waiting = build.full_page_values(app, with_state(app, "waitlist"), "2026-10-02")["free_band"]
    opened = build.full_page_values(app, with_state(app, "open"), "2026-10-02")["free_band"]
    assert waiting.count("lp-col-cta") == 0 and waiting.count(">Join the Waitlist</a>") == 1   # one list, one button
    assert opened.count("lp-col-cta") == 2 and ">Sign Up Free</a>" in opened and ">Try It Free for 30 Days</a>" in opened


def test_words_left_out_stop_the_build_with_a_plain_sentence():
    """A season's panel is first read on the first build of that season: a gap must stop the build by name, not
    as a KeyError on some Friday in December."""
    app = SIGNED[0]
    def broken(change):
        copy = json.loads(json.dumps(build.load_copy()[app["id"]]))
        change(copy["page"])
        return copy
    cases = [
        (lambda p: p.pop("signup"), "signup"),
        (lambda p: p["signup"].pop("ask"), "ask"),
        (lambda p: p["signup"]["waitlist"].pop("close_title"), "close_title"),
        (lambda p: p["year"].pop("more"), "more"),
        (lambda p: p["year"]["seasons"][2].pop("text"), "text"),
        (lambda p: p["panel"].update(picture="photo"), "picture"),
        (lambda p: p.pop("sample"), "sample"),   # winter's panel shows the sample
    ]
    for change, name in cases:
        with pytest.raises(SystemExit, match=name):
            build.full_page_values(app, broken(change), "2026-10-02")
    with pytest.raises(SystemExit, match="2026-10-02"):
        build.season_of("10/02/2026")


def test_no_page_offers_to_subscribe_until_there_is_a_pay_page(site):
    """Scott, 2026-10-05: Subscribe is the word for the pay page, and "we don't need a subscribe link on the
    carousel cards ... just Open and Try for Free". There is no pay page yet, so nothing a visitor can press,
    on any page of the site, says it (the paid level is still named: "With a Subscription")."""
    pages = sorted(site.glob("*.html"))
    assert len(pages) >= len(all_pages())
    for path in pages:
        for control in controls(path.read_text(encoding="utf-8")):
            assert not re.search(r"\bsubscrib(e|ing)\b", control["text"], re.I), (path.name, control["text"])
    assert not config.SHOW_PRICES   # when billing exists both change together, with a real pay page to go to


def test_the_built_pages_carry_every_sign_up_spot_and_hide_them_from_a_browser_that_uses_the_app(site):
    """Read from the finished pages, so a part dropped from a template shows up here. Every link onto the
    app's sign-up card is for new visitors only; the Open links that replace them are for the rest; and the
    page keeps its ordinary links (the sample, the year) for both."""
    copy = build.load_copy()
    import cards
    for app in SIGNED:
        su = build.signup(app, copy[app["id"]])
        page = (site / build.APP_PAGE.format(app["id"])).read_text(encoding="utf-8")
        v = build.full_page_values(app, copy[app["id"]], cards.current()["date"])
        for where in ("open_button", "fine", "sample_band", "free_band", "shot", "year_strip", "closing"):
            assert v[where] and v[where] in page, where
        found = controls(page)
        ways_in = [c for c in found if c["href"] == su["url"]]
        # header, top, panel, sample, lists, after the steps, under this week, close (the last two 2026-10-08)
        assert len(ways_in) == 8 and all(c["for"] == "visitor-only" for c in ways_in)
        into_app = [c for c in found if c["href"] == app["url"]]
        assert {c["for"] for c in into_app} == {"member-only", "visitor-only"}   # Open for one; "Have an invite?" for the other
        # the main button, the steps, this week (2026-10-18: no longer the menu or the phone's bar, where Sign In stays)
        assert sum(c["for"] == "member-only" for c in into_app) == 3
        forget = [c for c in found if c["tag"] == "button" and c["text"] == "Forget this"]
        assert len(forget) == 1 and forget[0]["for"] == "member-only"
        home = controls((site / "index.html").read_text(encoding="utf-8"))
        # the app's tile, and (Herd Planner, 2026-10-08) the button under the home page's three steps
        assert [c["for"] for c in home if c["href"] == su["url"] and c["text"] == su["button"]] == ["visitor-only"] * 2


def test_sign_up_links_go_only_on_pages_that_have_them(site):
    copy = build.load_copy()
    own = {build.APP_PAGE.format(a["id"]) for a in SIGNED}
    for name in all_pages():
        nav = site_nav((site / name).read_text(encoding="utf-8"))
        assert ("nav-signup" in nav) == (name in own), name
        assert ('class="site-nav has-signup"' in (site / name).read_text(encoding="utf-8")) == (name in own), name
    waitlist = build.signup(SIGNED[0], copy[SIGNED[0]["id"]])["url"]
    home = (site / "index.html").read_text(encoding="utf-8")
    notify = home[home.index('<section id="notify">'):]
    assert f'href="{waitlist}"' in notify   # "Join the list" opens the waitlist card itself


def test_the_header_makes_room_for_the_extra_button_below_a_wide_screen(site):
    """With the button (or the longer Open link) the header would wrap onto another row on tablets and small
    laptops. Below 1,100 px the labels shorten and How We Test leaves the row, only on pages that have the
    button or in a browser that uses an app. Measured in a browser at every width from 320 to 1,240 px."""
    styles = (site / "site.css").read_text(encoding="utf-8")
    block = styles[styles.index("@media (max-width: 1100px) {\n  .site-nav.has-signup"):]
    block = block[:block.index("\n}\n")]
    assert ".site-nav.has-signup > .nav-methods { display: none; }" in block
    assert ".nav-signup .wide, .nav-member .wide { display: none; }" in block
    assert ".nav-signup .narrow, .nav-member .narrow { display: inline; }" in block
    assert ".nav-signup .narrow, .nav-member .narrow { display: none; }" in styles[:styles.index(block)]
    for name in all_pages():   # How We Test is still reachable when it leaves the row
        page = (site / name).read_text(encoding="utf-8")
        assert page.count('href="methods.html"') >= 3, name   # the row, the Our Farm Apps menu, the footer
    copy = build.load_copy()
    for app in SIGNED:   # both labels are in the page for the styles to choose between
        nav = site_nav((site / build.APP_PAGE.format(app["id"])).read_text(encoding="utf-8"))
        assert '<span class="wide">Join the Waitlist</span><span class="narrow">Waitlist</span>' in nav
        assert f'Open {app["name"]} &#8594;' not in nav   # 2026-10-18: the menu keeps Sign In, never an Open link


# --- The panel beside the headline, and the year ----------------------------------------------------

def test_seasons_run_by_whole_months():
    from datetime import date
    assert [build.season_of(f"2026-{m:02d}-15") for m in range(1, 13)] == (
        ["winter"] * 2 + ["spring"] * 3 + ["summer"] * 3 + ["fall"] * 3 + ["winter"])
    assert build.season_of(date(2026, 11, 30)) == "fall" and build.season_of(date(2026, 12, 1)) == "winter"


@pytest.mark.parametrize("app", FULL, ids=lambda a: a["id"])
def test_the_year_has_four_seasons_and_marks_the_one_being_published(app):
    page = build.load_copy()[app["id"]]["page"]
    assert [s["id"] for s in page["year"]["seasons"]] == ["fall", "winter", "spring", "summer"]
    for day, name in (("2026-10-02", "Fall"), ("2027-01-08", "Winter"), ("2027-04-02", "Spring"), ("2027-07-02", "Summer")):
        strip = build.year_strip(page, build.season_of(day))
        assert strip.count('class="now"') == 1 and f'<li class="now"><span class="lp-season">{name} <i>Now</i>' in strip
        assert strip.count("<li") == 4
    # The paid level is a subscription, never "the plan"; and the heading promises no payback.
    strip = words(build.year_strip(page, "fall"))
    assert not re.search(r"\b(the|a|no|your) plans?\b", strip, re.I)
    for promise in ("earn", "pays for itself", "guarantee", "$"):
        assert promise not in page["year"]["title"].lower()


@pytest.mark.parametrize("app", FULL, ids=lambda a: a["id"])
def test_a_panels_words_always_sit_with_their_own_picture(app):
    """A season takes over the panel beside the headline only when it has a panel of its own; otherwise the
    standing one shows. So spring and summer, which have no picture of their own yet, never borrow another
    season's words, and no panel describes a picture it isn't sitting on. The sample never appears without
    its caption (made-up cattle; not an appraisal)."""
    copy = build.load_copy()[app["id"]]
    page = copy["page"]
    su = build.signup(app, copy)
    seen = set()
    for season in page["year"]["seasons"]:
        html = build.feature_panel(app, copy, su, season["id"])
        own = season.get("panel")
        panel = own or page["panel"]
        assert f'<h2>{build.e(panel["title"])}</h2>' in html and build.e(panel["text"]) in html
        assert (f'This {season["name"].lower()} &#183; with a subscription' in html) == bool(own), season["id"]
        if not own:
            assert '<span class="lp-tag">With a subscription</span>' in html
        assert ('class="shot showcase"' in html) == (panel["picture"] == "showcase")
        assert (build.e(page["sample"]["image"]) in html) == (panel["picture"] == "sample")
        assert (build.e(page["sample"]["caption"]) in html) == (panel["picture"] == "sample")
        assert 'href="#year"' in html and f'href="{su["url"]}"' in html
        seen.add(bool(own))
    assert seen == {True, False}   # today: fall and winter have their own, spring and summer wait for pictures
    assert "not an appraisal" in page["sample"]["caption"]


def test_the_built_page_follows_the_week_it_publishes_not_the_day_it_is_built(monkeypatch, tmp_path):
    """The Friday job publishes a week; the page's season comes from that week's date. Built here for a week in
    January, whatever today is: Winter is marked, and the lender's page sits beside the headline."""
    import cards
    week = {**cards.current(), "date": "2027-01-08"}
    monkeypatch.setattr(cards, "current", lambda: week)
    monkeypatch.setattr(build, "OUT", tmp_path / "docs")   # a scratch build, never the real docs/
    site = build.build()
    for app in FULL:
        page = (site / build.APP_PAGE.format(app["id"])).read_text(encoding="utf-8")
        seasons = {s["id"]: s for s in build.load_copy()[app["id"]]["page"]["year"]["seasons"]}
        assert '<li class="now"><span class="lp-season">Winter <i>Now</i>' in page
        assert f'<h2>{build.e(seasons["winter"]["panel"]["title"])}</h2>' in page
        assert build.e(seasons["fall"]["panel"]["title"]) not in page
        assert "This winter &#183; with a subscription" in page


# --- A browser that has used an app ------------------------------------------------------------------

def test_sign_in_is_on_every_page_for_everyone(site):
    """Scott, 2026-10-18: "what if you are someone like me that is on this page reading, then decides to sign-in?
    There is no link to sign in even on the menu bar." His A of notes/site-signin-2026-10-18.png: Sign In on every
    page for everyone, to My Farm (the one sign-in for every app), never swapped for an app's Open link. member.js
    still swaps the sign-up buttons in a page's body for an Open button: the script in the head (not deferred, so
    it runs before anything is drawn) and the rule that swaps them."""
    ids = " ".join(a["id"] for a in SIGNED)
    for path in sorted(site.glob("*.html")):
        page = path.read_text(encoding="utf-8")
        head = page[:page.index("</head>")]
        assert re.search(r'<script src="member\.js\?v=\w+" data-apps="%s" data-open-apps="%s"></script>'
                         % (re.escape(ids), re.escape(" ".join(a["id"] for a in build.load_apps() if build.open_url(a)))), head), path.name
        nav = site_nav(page)
        assert f'<a class="nav-signin" href="{config.ACCOUNT_URL}">Sign In</a>' in nav, path.name
        assert "nav-member" not in page and "nav-visitor" not in page, path.name
        for app in SIGNED:
            rule = (f'html[data-uses="{app["id"]}"] .visitor-only[data-app="{app["id"]}"], '
                    f'html:not([data-uses="{app["id"]}"]) .member-only[data-app="{app["id"]}"] {{ display: none !important; }}')
            assert rule in head, path.name


def test_without_the_script_a_page_is_what_a_new_visitor_sees(site):
    """The Open links are hidden by a rule that needs no script, and the sign-up links by one that only a
    remembered browser triggers: so no JavaScript, or storage switched off, leaves the visitor's page."""
    for name in all_pages():
        page = (site / name).read_text(encoding="utf-8")
        assert re.search(r'<html lang="en">', page) and "data-uses" not in page[page.index("<body"):], name
    styles = (site / "site.css").read_text(encoding="utf-8")
    assert "html[data-uses] .site-nav .nav-visitor" not in styles             # 2026-10-18: Sign In never hides


def test_the_script_keeps_one_word_in_the_browser_and_sends_nothing():
    """Read as text: what the script may and may not contain. What it does (remembers, forgets, tidies the
    address, ignores an app it doesn't know, leaves ordinary #links alone) is checked in a browser by
    herd-planner/tests/browser/site_links.js."""
    script = (build.STATIC / "member.js").read_text(encoding="utf-8")
    code = re.sub(r"//[^\n]*", "", script)
    for sends in ("fetch(", "XMLHttpRequest", "sendBeacon", "document.cookie", "new Image", ".src =", "WebSocket", "postMessage"):
        assert sends not in code
    # read, write, remove for each of two keys: "cpl.uses" (one app id) and, since 2026-10-20, "cpl.open" (app ids)
    assert code.count("localStorage.") == 6 and "sessionStorage" not in code
    assert 'var KEY = "cpl.uses", OPEN = "cpl.open";' in code
    # Only a mark for an app this site lists is acted on, and it is then taken out of the address, keeping the
    # page and anything after "?".
    assert r"var mark = /^#(uses|left)=([a-z0-9-]{1,40})$/.exec(location.hash);" in code
    assert "if (mark && (apps.indexOf(mark[2]) > -1 || menuApps.indexOf(mark[2]) > -1)) {" in code
    assert 'if (mark[1] === "uses") write(mark[2]); else if (read() === mark[2]) write(null);' in code
    assert 'keep(mark[1] === "uses" ? list.concat(mark[2]) : list);' in code   # #left takes the app off the menu list
    assert 'history.replaceState(null, "", location.pathname + location.search);' in code
    assert 'if (id && apps.indexOf(id) > -1) root.setAttribute("data-uses", id); else root.removeAttribute("data-uses");' in code
    # Forget this: forgets, redraws, and hands the keyboard on if its own line has gone.
    forget = code[code.index('closest("[data-forget-app]")'):]
    assert forget.index("write(null);") < forget.index("keep([]);") < forget.index("redraw();") < forget.index("next.focus()")


def test_the_privacy_page_says_what_the_browser_keeps(site):
    page = (site / "privacy.html").read_text(encoding="utf-8")
    note = page[page.index('<p id="this-browser">'):]
    note = words(note[:note.index("</p>")])
    assert "sets no cookies" in note and "never sent to us" in note and "not who you are" in note
    assert "data-forget-app" in page
    for app in FULL:   # the page that hides the links says why, and how to undo it
        full = (site / build.APP_PAGE.format(app["id"])).read_text(encoding="utf-8")
        assert 'href="privacy.html#this-browser"' in full and "data-forget-app" in full


@pytest.mark.skipif(not MASTER.exists(), reason="Herd Planner isn't checked out next to this project")
def test_herd_planner_reads_the_marks_this_site_sends_and_sends_the_ones_it_reads():
    """The two projects agree on a few small words. This site's links end in #waitlist, #signup and #signin, and
    the app opens that card; the app's link back ends in #uses=herd-planner or #left=herd-planner, and
    member.js reads those. If either side changes its words, change the other."""
    web = MASTER.parent / "src" / "herd_planner" / "web"
    app_js, first_screen = (web / "app.js").read_text(encoding="utf-8"), (web / "index.html").read_text(encoding="utf-8")
    cards_ = re.search(r"const CARD_MARK = /\^#\(([a-z|]+)\)\$/;", app_js).group(1).split("|")
    for state in build.SIGNUP.values():
        card = state["hash"].lstrip("#")
        assert card in cards_ and f'id="{card}-form"' in first_screen
    assert "signin" in cards_ and 'id="signin-form"' in first_screen
    assert '`${signedIn ? "uses" : "left"}=herd-planner`' in app_js


def test_the_test_figures_sit_in_answers_you_can_check_and_the_apps_row_has_a_heading(site):
    """Scott, 2026-10-08: two testing sections close together took a lot of room for the same thing, and the first
    looked plain. The three figures moved onto the green band of "Answers You Can Check", and the apps row now opens
    with its own heading (his option A), so this week's cards don't run straight into the app cards."""
    home = (site / "index.html").read_text(encoding="utf-8")
    week = home[home.index('<section class="week"'):home.index('<section class="tiles-band"')]
    assert "proof" not in week and "Tested before we trust it" not in home
    band = home[home.index('<div class="why-band">'):home.index('<div class="stories">')]
    assert band.count('<a href="methods.html#') == 4 and 'class="proof-stats why-proof"' in band   # four apps since 2026-10-18
    tiles = home[home.index('<section class="tiles-band"'):home.index('<section class="why"')]
    assert tiles.index("<h2>Try the Apps</h2>") < tiles.index('class="tiles"')
    assert home.count("<h2>Our Farm Apps</h2>") == 1                  # the full section further down keeps its name


def test_our_farm_apps_opens_on_a_green_band(site):
    """Scott, 2026-10-08: "Our Farm Apps" was barely bigger than the app names under it. He chose the deep-green
    band of "Answers You Can Check" (option A) for it."""
    home = (site / "index.html").read_text(encoding="utf-8")
    at = home.index("<h2>Our Farm Apps</h2>")
    assert home.rindex('<div class="head-band">', 0, at) > home.rindex("<section", 0, at)
    assert ".head-band {" in (site / "site.css").read_text(encoding="utf-8")


def test_how_it_works_and_our_promises_open_lighter_and_the_steps_end_with_herd_planner(site):
    """Scott, 2026-10-08: three green bands in a row were too much. How It Works and Our Promises got a lighter
    heading between thin deep-green lines (his option B), and after reading the three steps "the natural thing to do
    is open herd planner", so the steps end with its button and a way back to the other apps."""
    home = (site / "index.html").read_text(encoding="utf-8")
    for name in ("How It Works", "Our Promises"):
        at = home.index(f"<h2>{name}</h2>")
        section = home.rindex("<section", 0, at)
        assert "quiet-top" in home[section:home.index(">", section)]
        assert home.rfind('class="head-band"', section, at) == -1
    steps = home[home.index("<h2>How It Works</h2>"):home.index("<h2>Our Promises</h2>")]
    cta = steps[steps.index('class="steps-cta"'):]
    assert steps.index('class="steps"') < steps.index('class="steps-cta"')
    assert 'href="https://herd.cornerpostlogic.com/">Open Herd Planner' in cta and 'href="#our-apps"' in cta
    # Herd Planner is opening by invite: a new visitor gets Join the Waitlist, a browser that has used it Open
    assert 'class="btn visitor-only" data-app="herd-planner" href="https://herd.cornerpostlogic.com/#waitlist"' in cta
    assert 'class="btn member-only" data-app="herd-planner"' in cta
    assert "worth" not in cta        # the herd value is a paid tool after the trial (2026-09-29): promise only what's free
    css = (site / "site.css").read_text(encoding="utf-8")
    assert "section.quiet-top {" in css and "border-top: 6px solid var(--suite-deep-green)" in css



def test_the_herd_planner_page_says_whose_page_it_is_far_down_on_a_phone(site):
    """Scott, 2026-10-08: on a phone "What You Get" is far down the page and he forgot he was on Herd Planner's;
    and "A Subscription for Every Season" spoke of one subscription as if there were several. Both name the app."""
    page = (site / "herd-planner.html").read_text(encoding="utf-8")
    assert "<h2>What You Get with Herd Planner</h2>" in page
    assert '<h2 id="year">Herd Planner Through the Ranch Year</h2>' in page and "Subscription for Every Season" not in page


def test_built_in_says_what_the_company_and_apps_do_with_no_draft_left(site):
    """Scott, 2026-10-08: the "(Draft: ...)" line and the gray "Photo" circle near the foot of the home page were
    unfinished for anyone to see. They became what the company does and the four apps (his option 2), each linking
    to its own page, with the logo badge in place of a photo."""
    home = (site / "index.html").read_text(encoding="utf-8")
    block = home[home.index('<div class="founder">'):home.index('id="notify"')]
    assert "Draft" not in block and ">Photo<" not in block and 'class="founder-badge" src="brand/icon.svg"' in block
    links = re.findall(r'<li><a href="([a-z-]+\.html)">', block)
    assert len(links) == 4
    for page in links:
        assert (site / page).exists(), page


def test_the_ranch_year_leads_with_every_week_and_free_marks_only_records(site):
    """Scott, 2026-10-08: the season cards checked against what Herd Planner does today. The line under the
    heading leads with what happens every week, all year (the herd's worth and what changed, the Monday email),
    and "(always free)" only ever sits on record keeping, the Sept 29 rule (decisions are the subscription)."""
    year = build.load_copy()["herd-planner"]["page"]["year"]
    assert year["note"].startswith("Every week, all year:") and "Monday email" in year["note"]
    seasons = {s["id"]: s for s in year["seasons"]}
    assert "outlook" in seasons["summer"]["title"] and "scale or EID reader" in seasons["summer"]["text"]
    assert "nets you the most" in seasons["fall"]["text"] and "withdrawal dates" in seasons["spring"]["text"]
    for s in year["seasons"]:
        for part in s["text"].split(". "):
            if "(always free)" in part:
                assert any(w in part for w in ("records", "sale sheet", "Weigh days")), part
    page = (site / "herd-planner.html").read_text(encoding="utf-8")
    assert year["note"].replace("'", "&#x27;") in page


def test_each_test_figure_says_which_app_and_what_was_tested(site):
    """Scott, 2026-10-08, on a phone: "the percentage like 2.5% are out on their own. Hard to see what they belong
    to." Option C: a heading over them, and each figure in its own box with its app's logo, name and what was
    tested, before the number."""
    home = (site / "index.html").read_text(encoding="utf-8")
    band = home[home.index('<div class="why-band">'):home.index('<div class="stories">')]
    assert band.index("How each app did when we tested it") < band.index('class="proof-stats why-proof"')
    names = {"herd-planner": "Herd Planner", "corn-yield-predictor": "Yield Predictor", "farm-equipment-planner": "Equipment Planner"}
    for section, name in names.items():
        box = band[band.index(f'<a href="methods.html#{section}">'):]
        box = box[:box.index("</a>")]
        assert box.index(f"<span>{name}<small>") < box.index("<strong>")       # the app is named before its number
        assert (site / "suite" / "suite-logos" / f"{section}.svg").exists()
    css = (site / "site.css").read_text(encoding="utf-8")
    assert ".why-band .why-proof .proof-app {" in css and ".why-proof-head {" in css


def test_the_equipment_planner_page_fixes(site):
    """Scott, 2026-10-08 (option A): the chart is a line, so its guide says "point", not "bar"; its last label no
    longer reaches over the line; a page's single finding fills the row (words left, chart right); and the weekly
    card says why the number matters, with a link down to the finding that shows it."""
    page = (site / "farm-equipment-planner.html").read_text(encoding="utf-8")
    assert "Each point is how many days" in page and "Each bar is how many days" not in page
    assert ">0% from 22 days<" in page
    assert '<figure class="story split" id="own-or-hire">' in page
    story = page[page.index('<figure class="story split"'):page.index("</figure>", page.index('<figure class="story split"'))]
    assert story.index('<div class="story-words">') < story.index('<div class="story-chart">')
    card = page[page.index('<div class="stat-card">'):]
    card = card[:card.index("</div>")]
    assert "What it means:" in card and 'href="#own-or-hire"' in card
    for name in ("corn-yield-predictor.html",):          # every single-finding page (the Grazing Planner has two since 2026-10-18)
        other = (site / name).read_text(encoding="utf-8")
        assert '<figure class="story split"' in other and "What it means:" not in other
    home = (site / "index.html").read_text(encoding="utf-8")
    assert "story split" not in home                                            # the home page's cards are as before


def test_every_page_has_a_link_preview_and_names_its_publisher(site):
    """2026-10-12 (Scott, "barn pages and search"): Open Graph tags, so a shared link shows the page's title, its
    description and the Cornerpost Logic picture; and JSON-LD saying who publishes the site. Every built page,
    barn pages included."""
    pages = all_pages() + [p.name for p in site.glob("barn-*.html")]
    for name in pages:
        page = (site / name).read_text(encoding="utf-8")
        desc = re.search(r'<meta name="description" content="([^"]*)"', page).group(1)
        assert f'<meta property="og:description" content="{desc}">' in page, name
        url = re.search(r'<link rel="canonical" href="([^"]*)"', page).group(1)
        assert f'<meta property="og:url" content="{url}">' in page, name
        assert f'<meta property="og:image" content="{config.SITE_URL}brand/og-card.png">' in page, name
        blocks = [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page)]
        org = [b for b in blocks if b["@type"] == "Organization"]
        assert org and org[0]["name"] == config.NAME and org[0]["url"] == config.SITE_URL, name
    card = (site / "brand" / "og-card.png").read_bytes()
    assert card[:8] == b"\x89PNG\r\n\x1a\n" and int.from_bytes(card[16:20], "big") == 1200 \
        and int.from_bytes(card[20:24], "big") == 630                       # the size the tags promise


def test_barn_pages_carry_their_breadcrumbs_as_structured_data(site):
    """The trail the page shows (Barn Prices > state), as search engines read it: Home > Barn Prices > the barn."""
    for path in site.glob("barn-*.html"):
        page = path.read_text(encoding="utf-8")
        trail = next(json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page)
                     if '"BreadcrumbList"' in b)
        names = [i["name"] for i in trail["itemListElement"]]
        assert names[:2] == ["Home", "Barn Prices"] and trail["itemListElement"][-1]["item"] == config.SITE_URL + path.name


def test_the_header_spans_the_window():
    """Scott, 2026-10-12: on a wide screen the logo belongs at the left edge and the menu at the right, as in the apps,
    not inside the content column."""
    css = (ROOT / "static" / "site.css").read_text(encoding="utf-8")
    assert ".site-header > .wrap { max-width: none; padding: 0 clamp(20px, 2.5vw, 32px); }" in css


def test_the_privacy_page_says_what_sharing_results_keeps(site):
    """2026-10-12, with My Farm v0.26.0 (Share Your Results): the promises the share page makes, here too."""
    page = (site / "privacy.html").read_text(encoding="utf-8")
    item = page.split('id="shared-results"', 1)[1].split("</li>", 1)[0]
    for words in ("keep only the summary you confirm", "An uploaded file is read and deleted", "never\n        sell them",
                  "averages across at least 5 farms", "delete them in My Farm any time"):
        assert words in item, words


def test_the_privacy_page_says_what_your_fields_keeps(site):
    """2026-10-13, with My Farm v0.30.0 (yield maps in Your Fields): outlines and a kept yield map, only with a yes."""
    page = (site / "privacy.html").read_text(encoding="utf-8")
    item = page.split('id="your-fields"', 1)[1].split("</li>", 1)[0]
    for words in ("if you tick the box to keep it", "never the single readings", "seen only by you",
                  "Delete removes them for good",
                  "its outline (with no name or account) is sent to USDA's Soil Data Access",    # v0.31.0, soils
                  "the yields you type into a field's history are seen only by you",               # v0.32.0, history
                  "to USDA's Cropland Data Layer image service"):                                  # v0.33.0, crops
        assert words in " ".join(item.split()), words


def test_every_page_has_the_ask_a_question_button_hidden_until_it_is_on(site):
    """Suite version 9 (2026-10-12): the support assistant's round button, bottom right on every page (mockup
    notes/ask-a-question-mockup-2026-10-12.png). It starts hidden; the shared suite.js shows it only once My Farm
    says the assistant is switched on, so nobody meets a button that only says it's off."""
    button = ('<button type="button" class="suite-ask-fab suite-ask-hidden" data-suite-ask="site" '
              'data-suite-base="suite">Ask a Question</button>')
    for page in ("index.html", "about.html", "methods.html", "barns.html", "herd-planner.html"):
        html = (site / page).read_text(encoding="utf-8")
        assert button in html and html.index(button) < html.index('<script src="suite/suite.js'), page




def test_the_menu_shows_coming_soon_apps(tmp_path, monkeypatch):
    """Suite version 10 (Scott chose A of notes/coming-soon-options-2026-10-14.png; "It looks like this popout card
    needs it too"): an app still being built ("soon" in a group of suite-apps.json) shows greyed in Our Farm Apps,
    with Coming Soon and nothing to click, the same rows as the apps' Farm Apps menus."""
    html = build.mega_menu(build.load_apps())
    soon = [a for g in json.loads((ROOT / "static/suite/suite-apps.json").read_text(encoding="utf-8"))["groups"] for a in g.get("soon", [])]
    assert soon, "nothing is coming soon: this test can go"
    for app in soon:
        row = html[html.index(f'<div class="mega-app soon"><img src="soon/{app["id"]}.svg"'):]
        row = row[:row.index("</div>")]
        assert f"<b>{build.e(app['name'])}</b>" in row and "<em>Coming Soon</em>" in row and "href" not in row
        assert (ROOT / "static/soon" / f"{app['id']}.svg").exists()
    ranches = html[html.index("For Ranches"):html.index("For Farms")]
    assert ranches.index("Grazing Planner") < ranches.index("Hay &amp; Feed Planner")   # after the open apps


def test_the_menu_goes_through_the_app_s_sign_in_check_once_this_browser_has_used_it(site):
    """Scott, 2026-10-20: signed in on Herd Planner, then the company site, then the menu back to Herd Planner: "Herd
    planner doesn't see me as signed in." The menu opened this site's Herd Planner page, which shows Sign In to
    everyone. Then: "a sign in check needs to be done and then send the user to the actual app if signed in, or the
    splash page for herd planner if not." Each app's row keeps its page here as the link (what a new visitor, no
    JavaScript, or Copy Link gets) and carries the app's /open, which member.js uses once the app has sent this
    browser back with #uses=. How the rows switch in a browser is checked with Playwright (see the README)."""
    page = (site / "index.html").read_text(encoding="utf-8")
    menu = page[page.index('<details class="mega"'):page.index("</details>", page.index('<details class="mega"'))]
    rows = re.findall(r'<a class="mega-app" href="([^"]+)"([^>]*)>', menu)
    by_page = {href: rest for href, rest in rows}
    for app_id, path in build.OPENS.items():
        app = next(a for a in build.load_apps() if a["id"] == app_id)
        assert f' data-app="{app_id}" data-open="{app["url"].rstrip("/")}/{path}"' == by_page[f"{app_id}.html"]
    assert by_page["corn-yield-predictor.html"] == ""            # no sign-in there: always its page
    script = (build.STATIC / "member.js").read_text(encoding="utf-8")
    assert 'document.querySelectorAll("a[data-open][data-app]")' in script
    assert 'a.setAttribute("href", used.indexOf(a.getAttribute("data-app")) > -1 ? a.getAttribute("data-open") : page);' in script
    assert 'document.addEventListener("DOMContentLoaded", rows);' in script   # the menu comes after the script


@pytest.mark.skipif(not MASTER.exists(), reason="the apps aren't checked out next to this project")
def test_every_app_the_menu_opens_answers_open_and_sends_the_marks():
    """The other side of the menu: each app has the /open route and sends #uses=/#left= on its way back here."""
    apps = MASTER.parents[1]
    assert '@app.get("/open"' in (apps / "herd-planner" / "src" / "herd_planner" / "main.py").read_text(encoding="utf-8")
    gp = apps / "grazing-planner" / "src" / "grazeplan"
    if gp.exists():
        assert '@app.get("/open"' in (gp / "app.py").read_text(encoding="utf-8")
        assert '"uses" : "left"}=grazing-planner' in (gp / "web" / "session.js").read_text(encoding="utf-8")
    ep = apps / "farm-equipment-planner"
    if ep.exists():
        assert 'path("open/", views.open_from_site' in (ep / "core" / "urls.py").read_text(encoding="utf-8")
        assert '"=farm-equipment-planner"' in (ep / "static" / "js" / "menus.js").read_text(encoding="utf-8")


def test_signed_in_the_header_shows_the_menu_under_your_name(site):
    """Scott, 2026-10-20: "no matter which app I sign in to, when I go to the company home page it says Sign In as if I
    am not already. Maybe it should say Sign Out if I'm logged in?" He chose B of notes/site-signout-sheet-*: a menu
    under your first name with My Farm and Sign Out, as in the apps. Every page is drawn as a visitor sees it, with the
    menu hidden; account.js asks My Farm and swaps it in only on a yes. Walked through in Chromium against a local My
    Farm (see the README)."""
    menu = ('<details class="nav-me" hidden><summary><span class="nav-me-name">My Farm</span></summary>'
            '<div class="nav-me-panel"><a href="%s">My Farm</a><button type="button" class="nav-signout">Sign Out</button>'
            '</div></details>' % build.MY_FARM_HOME)
    for path in sorted(site.glob("*.html")):
        page = path.read_text(encoding="utf-8")
        header = page[page.index('<header class="suite-bar site-header">'):page.index("</header>")]
        assert header.count('<a class="nav-signin" href="%s">Sign In</a>' % build.e(config.ACCOUNT_URL)) == 2, path.name
        assert header.count(menu) == 2, path.name           # the menu bar's, and the phone bar's
        assert re.search(r'<script src="account\.js\?v=\w+" data-account="%s" defer></script>' % re.escape(config.ACCOUNT_ORIGIN), page), path.name
    css = (site / "site.css").read_text(encoding="utf-8")
    assert ".site-header .nav-me[hidden], .site-header .nav-signin[hidden] { display: none !important; }" in css
    assert ".suite-bar .site-nav > .nav-me { display: none !important; }" in css   # a phone uses the bar's


def test_the_header_script_asks_my_farm_yes_or_no_and_starts_as_a_visitor():
    script = (build.STATIC / "account.js").read_text(encoding="utf-8")
    code = re.sub(r"//[^\n]*", "", script)
    assert 'fetch(origin + "/site/status", { credentials: "include", cache: "no-store"' in code
    assert "var yes = !!(answer && answer.signed_in === true);" in code      # only a plain yes swaps
    assert "span.textContent = label;" in code                              # the name as text, never as HTML
    assert 'fetch(origin + "/site/sign-out", { method: "POST", credentials: "include", cache: "no-store" })' in code
    assert "localStorage" not in code and "document.cookie" not in code and "innerHTML" not in code
    assert code.count("fetch(") == 2                                          # those two, and nothing else


@pytest.mark.skipif(not (ROOT.parent / "farm-account").exists(), reason="My Farm isn't checked out next to this project")
def test_my_farm_answers_this_site_and_only_this_site():
    router = (ROOT.parent / "farm-account" / "src" / "farm_account" / "routers" / "site_sign_in.py").read_text(encoding="utf-8")
    assert '@router.get("/status"' in router and '@router.post("/sign-out"' in router
    assert 'SITE_ORIGINS = {"https://cornerpostlogic.com", "https://www.cornerpostlogic.com"}' in router
    assert config.SITE_URL.rstrip("/") in router
