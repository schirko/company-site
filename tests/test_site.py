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


def test_sign_in_is_in_every_page_menu(site):
    for name in all_pages():
        page = (site / name).read_text(encoding="utf-8")
        nav = page[page.index('<nav class="site-nav"'):page.index("</nav>")]
        assert f'href="{config.ACCOUNT_URL}">Sign In</a>' in nav, name
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
    proof = home[home.index('class="proof-stats"'):home.index("</section>", home.index('class="proof-stats"'))]
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
    why = home[home.index("<h2>Why Use Our Apps</h2>"):]
    lede = why[:why.index('<div class="stories">')]
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
    # Two buttons: into the app, and down to the sample (a link on this page, which the link test follows).
    assert f'<a class="btn" href="{build.e(app["url"])}">Open {build.e(app["name"])}</a>' in page
    assert f'<a class="btn ghost" href="#{sample["id"]}">{build.e(sample["button"])}</a>' in page
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
