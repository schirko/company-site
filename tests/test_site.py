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
