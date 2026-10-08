"""The company site builds, every page carries the name from config.py, and nothing links nowhere."""

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
    tiles = {"herd-planner": "#243b2f", "corn-yield-predictor": "#4a3520", "grazing-planner": "#2f5d5a", "farm-equipment-planner": "#23374d"}
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
    """Sign In goes to the suite account, except on the page of an app with sign-up links, where it goes to
    that app's own sign-in card (a Herd Planner account is not a Your Account sign-in)."""
    copy = build.load_copy()
    own = {build.APP_PAGE.format(a["id"]): build.signup(a, copy[a["id"]]) for a in build.load_apps()}
    for name in all_pages():
        nav = site_nav((site / name).read_text(encoding="utf-8"))
        where = own[name]["signin"] if own.get(name) else config.ACCOUNT_URL
        assert f'href="{where}">Sign In</a>' in nav and nav.count(">Sign In</a>") == 1, name
        assert "<summary>Our Farm Apps</summary>" in nav, name


def test_apps_in_development_get_an_honest_tile_and_nothing_else(site):
    """A tile on the home page (tag, Get notified), but no app page, no Farm Apps menu entry, no footer link."""
    copy = json.loads((ROOT / "content/apps.json").read_text(encoding="utf-8"))
    suite_ids = {a["id"] for a in build.load_apps()}
    home = (site / "index.html").read_text(encoding="utf-8")
    for app in copy["in_development"]:
        assert app["id"] not in suite_ids, f"{app['id']} is live: remove it from in_development"
        assert (site / "soon" / f"{app['id']}.svg").exists()
        tile = home[home.index(f'soon/{app["id"]}.svg'):]
        tile = tile[:tile.index("</div>")]
        assert "In development" in tile and 'href="#notify"' in tile and app["name"] in tile
        assert not (site / build.APP_PAGE.format(app["id"])).exists()
    assert 'id="notify"' in home
    assert len(re.findall(r'class="tile[ "]', home)) == len(suite_ids) + len(copy["in_development"])


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
    methods = (site / "methods.html").read_text(encoding="utf-8")
    for section in ("herd-planner", "corn-yield-predictor", "farm-equipment-planner"):
        assert f'<a href="methods.html#{section}"><strong>' in proof
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
    order = [page.index(mark) for mark in ("<h1>", f'id="{sample["id"]}"', 'id="what-you-get"', "<h2>How It Works</h2>",
                                           "lp-weekly", "<h2>What the Numbers Show</h2>", "<h2>Where the Number Comes From</h2>")]
    assert order == sorted(order)
    # Two buttons: the way in for someone new (or, for a browser that has used the app, straight into it), and
    # down to the sample (a link on this page, which the link test follows).
    su = build.signup(app, copy)
    top = page[page.index('<p class="lp-cta">'):page.index('</p>', page.index('<p class="lp-cta">'))]
    assert f'<a class="btn visitor-only" data-app="{app["id"]}" href="{su["url"]}">{su["button"]}</a>' in top
    assert f'<a class="btn member-only" data-app="{app["id"]}" href="{build.e(app["url"])}">Open {build.e(app["name"])}</a>' in top
    assert f'<a class="btn ghost" href="#{sample["id"]}">{build.e(sample["button"])}</a>' in top
    order = [page.index(mark) for mark in ('id="what-you-get"', 'id="year"', "<h2>How It Works</h2>")]
    assert order == sorted(order)
    assert len(copy["page"]["steps"]) == page.count("<li><b>") == 5


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
    assert [(c["href"], c["for"]) for c in nav if c["for"] != "member-only"] == [(base + "#signin", None), (base + card, "visitor-only")]


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
        assert len(ways_in) == 6 and all(c["for"] == "visitor-only" for c in ways_in)   # header, top, panel, sample, lists, close
        into_app = [c for c in found if c["href"] == app["url"]]
        assert {c["for"] for c in into_app} == {"member-only", "visitor-only"}   # Open for one; "Have an invite?" for the other
        assert sum(c["for"] == "member-only" for c in into_app) == 2             # the menu, and the main button
        forget = [c for c in found if c["tag"] == "button" and c["text"] == "Forget this"]
        assert len(forget) == 1 and forget[0]["for"] == "member-only"
        home = controls((site / "index.html").read_text(encoding="utf-8"))
        assert [c["for"] for c in home if c["href"] == su["url"] and c["text"] == su["tile"]] == ["visitor-only"]


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
    assert ".site-nav.has-signup > .nav-methods, html[data-uses] .site-nav > .nav-methods { display: none; }" in block
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
        assert (f'<span class="wide">Open {app["name"]} &#8594;</span><span class="narrow">'
                f'{copy[app["id"]]["member_short"]} &#8594;</span>') in nav


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

def test_every_page_can_offer_the_app_in_place_of_sign_in(site):
    """Scott, 2026-10-05: "when I'm logged in on herd planner and then go to the home page ... the link up top
    says Sign In as if I am not already logged in." The site can't see an app's sign-in, so member.js remembers
    the browser. In every page: the script in the head (not deferred, so it runs before anything is drawn),
    the app's Open link in the menu, and the rule that swaps them."""
    ids = " ".join(a["id"] for a in SIGNED)
    for path in sorted(site.glob("*.html")):
        page = path.read_text(encoding="utf-8")
        head = page[:page.index("</head>")]
        assert re.search(r'<script src="member\.js\?v=\w+" data-apps="%s"></script>' % re.escape(ids), head), path.name
        nav = site_nav(page)
        for app in SIGNED:
            assert (f'<a class="nav-signin nav-member member-only" data-app="{app["id"]}" href="{app["url"]}">'
                    in nav), path.name
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
    assert "html[data-uses] .site-nav .nav-visitor { display: none; }" in styles


def test_the_script_keeps_one_word_in_the_browser_and_sends_nothing():
    """Read as text: what the script may and may not contain. What it does (remembers, forgets, tidies the
    address, ignores an app it doesn't know, leaves ordinary #links alone) is checked in a browser by
    herd-planner/tests/browser/site_links.js."""
    script = (build.STATIC / "member.js").read_text(encoding="utf-8")
    code = re.sub(r"//[^\n]*", "", script)
    for sends in ("fetch(", "XMLHttpRequest", "sendBeacon", "document.cookie", "new Image", ".src =", "WebSocket", "postMessage"):
        assert sends not in code
    assert code.count("localStorage.") == 3 and "sessionStorage" not in code   # read, write, remove: one key
    assert 'var KEY = "cpl.uses";' in code
    # Only a mark for an app this site lists is acted on, and it is then taken out of the address, keeping the
    # page and anything after "?".
    assert r"var mark = /^#(uses|left)=([a-z0-9-]{1,40})$/.exec(location.hash);" in code
    assert "if (mark && apps.indexOf(mark[2]) > -1) {" in code
    assert 'if (mark[1] === "uses") write(mark[2]); else if (read() === mark[2]) write(null);' in code
    assert 'history.replaceState(null, "", location.pathname + location.search);' in code
    assert 'if (id && apps.indexOf(id) > -1) root.setAttribute("data-uses", id); else root.removeAttribute("data-uses");' in code
    # Forget this: forgets, redraws, and hands the keyboard on if its own line has gone.
    forget = code[code.index('closest("[data-forget-app]")'):]
    assert forget.index("write(null);") < forget.index("show();") < forget.index("next.focus()")


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
    assert band.count('<a href="methods.html#') == 3 and 'class="proof-stats why-proof"' in band
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
    assert 'href="https://herd-planner.onrender.com/">Open Herd Planner' in cta and 'href="#our-apps"' in cta
    assert "worth" not in cta        # the herd value is a paid tool after the trial (2026-09-29): promise only what's free
    css = (site / "site.css").read_text(encoding="utf-8")
    assert "section.quiet-top {" in css and "border-top: 6px solid var(--suite-deep-green)" in css



def test_the_herd_planner_page_says_whose_page_it_is_far_down_on_a_phone(site):
    """Scott, 2026-10-08: on a phone "What You Get" is far down the page and he forgot he was on Herd Planner's;
    and "A Subscription for Every Season" spoke of one subscription as if there were several. Both name the app."""
    page = (site / "herd-planner.html").read_text(encoding="utf-8")
    assert "<h2>What You Get with Herd Planner</h2>" in page
    assert '<h2 id="year">Herd Planner Through the Ranch Year</h2>' in page and "Subscription for Every Season" not in page
