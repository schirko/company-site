"""Build the company website into docs/, ready for GitHub Pages.

    python build.py

Why a build step at all, for a five-page site? Two things would otherwise be typed
by hand on every page and drift apart:

- the company name, which isn't chosen yet (it lives in config.py), and
- the list of apps, which already lives in static/suite/suite-apps.json, the same
  file the apps' "Farm apps" menus read.

So pages are written once in templates/ with ${placeholders}, and this script fills
them in. It uses only Python's standard library (string.Template), so there is
nothing to install. GitHub Pages then serves the docs/ folder as it is.
"""

import hashlib
import html
from datetime import date
import json
import shutil
import urllib.parse
from pathlib import Path
from string import Template

import cards
import barn_pages
import charts
import hero
import config

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
SHOTS = STATIC / "shots"  # each app on a computer and a phone (app_shot)
CONTENT = ROOT / "content"
OUT = ROOT / "docs"

HERD_PLANNER_TERMS = "https://herd-planner.onrender.com/app/terms.html"

# Each page: output file, template, <title> suffix, description, and which nav link is current.
PAGES = [
    ("index.html", "index.html", None, "Decision tools for ranchers and farmers: herd, crop and machinery decisions from your own records and public data.", None),
    ("about.html", "about.html", "About", "Who builds the apps, and how.", "about"),
    ("methods.html", "methods.html", "How We Test", "How each app's models are tested, the results, and where each one falls short.", "methods"),
    ("privacy.html", "privacy.html", "Privacy", "How the apps handle your email and your records.", "privacy"),
    ("404.html", "404.html", "Page not found", "That page isn't here.", None),
]


# Each app's own page on this site (built from templates/app.html), named by app id.
APP_PAGE = "{}.html"

# The Our Farm Apps menu in the header (chosen 2026-09-30, option C): apps sorted by operation, then the free
# tools and How We Test. Every live app must be in exactly one group (a test checks), so a new app needs a line here.
OPERATIONS = [
    ("For Ranches", "Cattle and grass", ["herd-planner", "grazing-planner"]),
    ("For Farms", "Crops and machines", ["corn-yield-predictor", "farm-equipment-planner"]),
]
HISTORY_WEEKS = 12  # weeks listed on each app page


def load_apps():
    return json.loads((STATIC / "suite" / "suite-apps.json").read_text(encoding="utf-8"))["apps"]


def e(text):
    """Escape text for HTML: an app name with an '&' in it must not break the page."""
    return html.escape(text, quote=True)


def mega_menu(apps) -> str:
    """The header's Our Farm Apps menu: a <details> element (opens without JavaScript; static/menu.js closes it on
    a click elsewhere, Escape or a chosen link). Each app links to its page here, with its logo and one line."""
    by_id = {a["id"]: a for a in apps}

    def app_link(a):
        return (f'          <a class="mega-app" href="{APP_PAGE.format(e(a["id"]))}">'
                f'<img src="suite/suite-logos/{e(a["id"])}.svg" alt="" width="40" height="40">'
                f'<span><b>{e(a["name"])}</b><small>{e(a["what"])}</small></span></a>')
    groups = []
    for title, lead, ids in OPERATIONS:
        links = "\n".join(app_link(by_id[i]) for i in ids if i in by_id)
        if links:
            groups.append(f'        <div class="mega-op">\n          <p class="mega-op-title">{e(title)}</p>\n'
                          f'          <p class="mega-op-lead">{e(lead)}</p>\n{links}\n        </div>')
    return "\n".join([
        '<details class="mega" data-mega>',
        '      <summary>Our Farm Apps</summary>',
        '      <div class="mega-panel">',
        *groups,
        '        <div class="mega-more">',
        '          <div><p class="mega-head">Free for everyone</p>',
        '          <a href="barns.html">Barn Prices<small>This week&#8217;s feeder prices at your barn</small></a>',
        '          <a href="index.html#this-week">This week in your county<small>Steer price, trend yield, grass, field days</small></a></div>',
        '          <div><p class="mega-head">Why trust it</p>',
        '          <a href="methods.html">How We Test<small>Real results, and where we fell short</small></a></div>',
        '        </div>',
        f'        <p class="mega-foot"><span>One account for every app.</span><a href="{e(config.ACCOUNT_URL)}">Your Account &#8594;</a></p>',
        '      </div>',
        '    </details>'])


def load_copy():
    """The site's longer words about each app (content/apps.json), keyed by app id."""
    return json.loads((CONTENT / "apps.json").read_text(encoding="utf-8"))


def short_county(week) -> str:
    """ "Frontier County" -> "Frontier Co." for the small line under a tile's number."""
    return week["place"]["county"].replace(" County", " Co.")


def tile_stat(app_id, week):
    """(number, unit, small line, tone) for an app tile's top right corner: this week's number from the county
    of the week (the same cards the live panel and app pages use), or None when there isn't one this week
    (a stale steer price, or an Iowa county for the Grazing Planner)."""
    card = week["cards"].get(app_id)
    if not card:
        return None
    where = short_county(week)
    if app_id == cards.HERD:
        barn = card["market"].rsplit(",", 1)[-1].strip()  # "Bassett Livestock Auction, Bassett NE" -> "Bassett NE"
        return f'${card["value"]:,.0f}', "/cwt", f"550 lb steer, {barn}", ""
    if app_id == cards.CORN:
        return f'{card["value"]:,.0f}', " bu/ac", f"{where} trend corn", ""
    if app_id == cards.EQUIP:
        return f'{card["value"]:,.0f}', " of 61 days", f"{where} fall field days", ""
    if app_id == cards.GRAZE:
        pct = round(abs(card["value"]) * 100)
        small = f'{where} grass, {card.get("season", "")}'.rstrip(", ")
        if pct <= 2:
            return "About", " normal", small, ""
        if card["value"] < 0:  # red means the downside, always with an arrow and words
            return f"\u25bc {pct}%", " below normal", small, "down"
        return f"\u25b2 {pct}%", " above normal", small, ""
    return None


def app_tile(app, copy, week):
    """A big tile in the opening row: the whole tile is the link, so it's easy to hit on a phone. Top right:
    this week's number from the app (tile_stat); bottom right: free to try, and the starting price once
    billing exists (config.SHOW_PRICES)."""
    stat = tile_stat(app["id"], week)
    stat_html = ""
    if stat:
        number, unit, small, tone = stat
        detail = week["cards"][app["id"]]["detail"]
        stat_html = (f'<span class="tile-stat" title="{e(detail)}"><span class="tile-number">'
                     f'<b class="{tone}">{e(number)}</b>{e(unit)}</span><small>{e(small)}</small></span>')
    inner = f"""<span class="tile-top"><img src="suite/suite-logos/{e(app["id"])}.svg" alt="" width="56" height="56">{stat_html}</span>
        <span class="tile-words"><strong>{e(app["name"])}</strong><span>{e(copy["question"])}</span></span>"""
    price = (f'<br>Plan from <b>{e(copy["price_from"])}/mo</b>' if config.SHOW_PRICES and copy.get("price_from") else "")
    if app["url"]:
        return f"""      <a class="tile" href="{e(app["url"])}">
        {inner}
        <span class="tile-bottom"><span class="btn small" aria-hidden="true">Open</span><span class="tile-price">Free to try{price}</span></span>
      </a>"""
    later = (f'<span class="tile-price">Plan from <b>{e(copy["price_from"])}/mo</b></span>'
             if config.SHOW_PRICES and copy.get("price_from") else "")
    return f"""      <div class="tile soon">
        {inner}
        <span class="tile-bottom"><span class="status">Coming soon</span>{later}</span>
      </div>"""


def dev_tile(app):
    """An app being built (content/apps.json "in_development"): its question, an honest tag, and a way to
    hear when it opens. Not a link to an app, and not in the Farm Apps menu until it exists."""
    return f"""      <div class="tile dev">
        <img src="soon/{e(app["id"])}.svg" alt="" width="56" height="56">
        <span class="tile-words"><span class="tag">In development</span><strong>{e(app["name"])}</strong><span>{e(app["question"])}</span></span>
        <a class="btn small ghost" href="#notify">Get notified</a>
      </div>"""


def app_shot(app, copy):
    """The app on a computer (its real header joined to a real answer) with the same answer on a phone in
    front: static/shots/<id>-computer.jpg and -phone.jpg, taken from the running app. Until an app has
    both pictures it keeps the plain placeholder."""
    computer, phone = SHOTS / f'{app["id"]}-computer.jpg', SHOTS / f'{app["id"]}-phone.jpg'
    if not (computer.exists() and phone.exists()):
        return f'<div class="placeholder shot">Screenshot of {e(app["name"])}</div>'
    where = urllib.parse.urlsplit(app["url"]).netloc if app["url"] else "Coming soon"
    return f"""<figure class="shot showcase">
        <div class="browser"><div class="bar" aria-hidden="true"><i></i><i></i><i></i><span>{e(where)}</span></div>
          <img src="shots/{e(app["id"])}-computer.jpg" alt="{e(copy["shot_alt"])}" width="1100" height="825" loading="lazy"></div>
        <div class="phone"><img src="shots/{e(app["id"])}-phone.jpg" alt="" loading="lazy"></div>
      </figure>"""


def app_row(app, copy, flip):
    """One app's section: a screenshot space beside who it's for, what it does, and a button."""
    points = "\n".join(f"          <li>{e(p)}</li>" for p in copy["points"])
    button = (f'<a class="btn" href="{e(app["url"])}">Open {e(app["name"])}</a>' if app["url"]
              else '<span class="status">Coming soon</span>')
    return f"""    <div class="app-row{' flip' if flip else ''}" id="{e(app["id"])}">
      {app_shot(app, copy)}
      <div>
        <p class="eyebrow">{e(copy["audience"])}</p>
        <h3>{e(app["name"])}</h3>
        <ul class="points">
{points}
        </ul>
        <p class="meta">{e(copy["note"])}</p>
        <p>{button} <a class="more" href="{APP_PAGE.format(e(app["id"]))}">This week and how it works</a></p>
      </div>
    </div>"""


def app_line(app, with_status=True):
    name = f'<a href="{e(app["url"])}">{e(app["name"])}</a>' if app["url"] else e(app["name"])
    status = "" if app["url"] or not with_status else " (coming soon)"
    return f"      <li>{name}: {e(app['what'])}{status}.</li>"


def terms_line(app):
    if app["id"] == "herd-planner":
        return f'      <li>Herd Planner: <a href="{HERD_PLANNER_TERMS}">terms of use and privacy</a>.</li>'
    if app["url"]:
        return f"      <li>{e(app['name'])}: no account and nothing personal collected; its disclaimer is on every page.</li>"
    return f"      <li>{e(app['name'])}: its terms will be published when it opens.</li>"


# --- The weekly stat cards (cards.py picks the place and keeps the numbers) ----------------------


def nice_date(iso):
    d = date.fromisoformat(iso)
    return f"{d:%b} {d.day}, {d.year}"


def stat_card(app, card, week, link=True):
    """One number with its meaning and its source. On the home page the whole card links to the
    app's page on this site."""
    if card:
        foot = f"Source: {e(card['source'])}"  # the sale date is already in the detail
        inner = f"""<span class="stat-label">{e(card["label"])}</span>
        <span class="stat-headline">{e(card["headline"])}</span>
        <span class="stat-detail">{e(card["detail"])}</span>
        <span class="stat-source">{foot}</span>"""
    else:
        inner = f"""<span class="stat-label">550 lb steer, this week</span>
        <span class="stat-detail">No fresh sale-barn price for {e(week["place"]["state_name"])} this week.
          Prices update every Friday.</span>"""
    if link:
        return f"""      <a class="stat-card" href="{APP_PAGE.format(e(app["id"]))}">
        <span class="stat-app"><img src="suite/suite-logos/{e(app["id"])}.svg" alt="" width="28" height="28"> {e(app["name"])}</span>
        {inner}
      </a>"""
    return f"""      <div class="stat-card">
        {inner}
      </div>"""


def history_table(app_id, weeks):
    """Recent weeks for one app: the place and its number, newest first."""
    rows = []
    for w in weeks:
        c = w["cards"].get(app_id)
        if not c:
            continue
        when = nice_date(w["date"])
        where = f'{e(w["place"]["county"])}, {e(w["place"]["state"])}'
        if app_id == cards.HERD:
            cells = [when, e(c["market"]), f'${c["value"]:,.0f}/cwt', f'${c["low"]:,.0f} to ${c["high"]:,.0f}']
        elif app_id == cards.CORN:
            cells = [when, where, f'{c["value"]:.0f} bu/acre', f'{c["low"]:.0f}']
        else:
            cells = [when, where, f'{c["value"]:.0f} days', f'{c["low"]:.0f} days']
        rows.append("          <tr>" + "".join(f"<td>{x}</td>" for x in cells) + "</tr>")
        if len(rows) == HISTORY_WEEKS:
            break
    heads = {cards.HERD: ("Week of", "Sale barn", "550 lb steer", "8 in 10 sales"),
             cards.CORN: ("Week of", "County", "Trend yield", "1-in-10 low"),
             cards.EQUIP: ("Week of", "County", "Typical fall", "Wet fall (1 in 10)")}[app_id]
    if not rows:
        return '    <p class="note">The first week is on its way.</p>'
    head = "".join(f"<th>{h}</th>" for h in heads)
    return f"""    <div class="table-scroll">
      <table class="results history">
        <thead><tr>{head}</tr></thead>
        <tbody>
{chr(10).join(rows)}
        </tbody>
      </table>
    </div>"""


# The apps with a card in the Friday county-of-the-week job (cards.py). Others (the Grazing Planner, so
# far) have an app page without "This Week" and "Recent Weeks".
WEEKLY = (cards.HERD, cards.CORN, cards.EQUIP)

APP_METHOD = {
    cards.HERD: ("Herd Planner fits a price model to USDA auction reports from the sale barn nearest the "
                 "week's county that sold in the last three weeks (its own state first, then neighbors; "
                 "otherwise Oklahoma City, the deepest weekly feeder sale). The range comes from testing the "
                 "model on sales it never saw: 8 in 10 real sales landed inside it."),
    cards.CORN: ("A straight-line trend through the county's USDA corn yields since 2000 says what a normal "
                 "year looks like now. The low end is the 10th percentile of each year's yield relative to its "
                 "trend: 1 year in 10 does worse. It's the county's recent normal and its downside, not a "
                 "forecast of this season."),
    cards.EQUIP: ("A day counts as workable when it had under 2.5 mm of rain and under 12.5 mm over the two "
                  "days before, the same rule the Equipment Planner uses to price harvest delays. We count "
                  "those days from October 1 to November 30 in every fall since 2000: the typical fall is the "
                  "median, the wet fall the 10th percentile. It counts rain only, not snow or frozen ground."),
    "grazing-planner": ("Each county's grass is the Rangeland Analysis Platform's satellite estimate of forage grown on "
                        "its grassland (cropland masked out). \"Normal\" is the county's average over the 10 seasons "
                        "before. The forecast learns from every earlier season how the weather so far, and the grass "
                        "already grown, relate to how the season ends; its range comes from how far off it was in "
                        "those seasons. Head counts use the standard animal-unit-month arithmetic with a 25% harvest "
                        "on native range."),
}
APP_SOURCE = {
    cards.HERD: "USDA AMS Market News auction reports",
    cards.CORN: "USDA NASS county corn yields, all practices, 2000 on",
    cards.EQUIP: "NASA POWER daily rainfall, 2000 on",
    "grazing-planner": "Rangeland Analysis Platform (USDA Agricultural Research Service), NASA POWER weather",
}
HISTORY_NOTE = {
    cards.HERD: "Prices are what the model said that week, at the barn nearest that county.",
    cards.CORN: "These are each county's trend yields, so they change once a year, not week to week.",
    cards.EQUIP: "These come from 26 falls of weather, so a county's numbers change only once a year.",
}


def week_blocks(app, week, weeks):
    """This Week and Recent Weeks for an app in the Friday job; for other apps, how to get this season's
    numbers from the app itself."""
    if app["id"] not in WEEKLY:
        link = (f'<a href="{e(app["url"])}">Open {e(app["name"])}</a>' if app["url"] else e(app["name"]))
        return (f"""        <h2>This Season</h2>
        <p>Pick your county in the app: {link}. The forecasts update every Monday from April to November,
          as new satellite and weather data come in.</p>""", "")
    place = week["place"]
    card = stat_card(app, week["cards"].get(app["id"]), week, link=False)
    history = history_table(app["id"], weeks)
    return (f"""        <h2>This Week: {e(f'{place["county"]}, {place["state_name"]}')}</h2>
{card}""", f"""    <h2>Recent Weeks</h2>
    <p class="section-lede">Each Friday we pick a farm county and add a line here. {e(HISTORY_NOTE[app["id"]])}</p>
{history}
""")


def app_page_values(app, copy, week, weeks):
    week_block, history_block = week_blocks(app, week, weeks)
    return {
        "app_id": e(app["id"]), "app_name": e(app["name"]), "question": e(copy["question"]),
        "audience": e(copy["audience"]), "note": e(copy["note"]),
        "points": "\n".join(f"          <li>{e(p)}</li>" for p in copy["points"]),
        "open_button": (f'<a class="btn" href="{e(app["url"])}">Open {e(app["name"])}</a>' if app["url"]
                        else '<span class="status">Coming soon</span>'),
        "week_block": week_block, "history_block": history_block,
        "method": e(APP_METHOD[app["id"]]), "source": e(APP_SOURCE[app["id"]]),
    }


def sitemap(pages, lastmod):
    urls = "\n".join(f"  <url><loc>{e(config.SITE_URL + ('' if p == 'index.html' else p))}</loc>"
                     f"<lastmod>{lastmod}</lastmod></url>" for p in pages)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "\n</urlset>\n")


# --- "Why Use Our Apps": one real finding per story, drawn by charts.py -------------------------


def load_stories():
    return json.loads((CONTENT / "stories.json").read_text(encoding="utf-8"))["stories"]


def story_block(story, apps_by_id, heading="h3", link=True):
    app = apps_by_id[story["app"]]
    more = (f'<p class="story-link"><a href="{APP_PAGE.format(e(app["id"]))}">More about {e(app["name"])}</a></p>'
            if link else "")
    return f"""      <figure class="story" id="{e(story["id"])}">
        <p class="stat-app"><img src="suite/suite-logos/{e(app["id"])}.svg" alt="" width="24" height="24"> {e(app["name"])}</p>
        <{heading}>{e(story["title"])}</{heading}>
        <p class="story-headline">{e(story["headline"])}</p>
        <p class="chart-title">{e(story["chart_title"])}</p>
        {charts.draw(story)}
        <figcaption>
          <p>{e(story["takeaway"])}</p>
          <p class="note">{e(story["caution"])}</p>
          <p class="source">Source: {e(story["source"])}</p>
        </figcaption>
        {charts.table(story)}
{more}
      </figure>"""


def contact_sentence():
    if config.EMAIL:
        return f'Write to us at <a href="mailto:{e(config.EMAIL)}">{e(config.EMAIL)}</a>.'
    return "To reach us, use the Tell us button in Herd Planner. It comes straight to us."


VERSIONED = ("suite/suite.css", "site.css", "suite/suite.js", "slider.js", "panel.js", "menu.js")


def versioned(page: str) -> str:
    """Add ?v=<short hash of the file> to each stylesheet and script link. Browsers keep these files for a while
    (GitHub Pages says 10 minutes); a new version gets a new address, so nobody sees new pages with old styles."""
    for name in VERSIONED:
        tag = hashlib.sha256((STATIC / name).read_bytes()).hexdigest()[:10]
        page = page.replace(f'"{name}"', f'"{name}?v={tag}"')
    return page


def build():
    apps = load_apps()
    copy = load_copy()
    week = cards.current()
    barn_data = cards.load_barns()
    all_barns = barn_data["barns"]
    barn_href = lambda slug: barn_pages.page_name(str(slug), all_barns[str(slug)]) if str(slug) in all_barns else None
    stories = load_stories()
    apps_by_id = {a["id"]: a for a in apps}
    weeks = cards.load_weeks()
    herd = next(a for a in apps if a["id"] == "herd-planner")
    values = {
        "name": e(config.NAME),
        "tagline": e(config.TAGLINE),
        "location": e(config.LOCATION),
        "year": str(config.YEAR),
        "herd_url": e(herd["url"] or "#apps"),
        "app_tiles": "\n".join([app_tile(a, copy[a["id"]], week) for a in apps]
                               + [dev_tile(d) for d in copy.get("in_development", [])]),
        "account_url": e(config.ACCOUNT_URL),
        "app_rows": "\n".join(app_row(a, copy[a["id"]], i % 2 == 1) for i, a in enumerate(apps)),
        "app_list": "\n".join(app_line(a) for a in apps),
        "terms_list": "\n".join(terms_line(a) for a in apps),
        "contact_sentence": contact_sentence(),
        "mega_menu": mega_menu(apps),
        "footer_apps": "\n".join(f'      <a href="{APP_PAGE.format(e(a["id"]))}">{e(a["name"])}</a>' for a in apps),
        "week_place": e(f'{week["place"]["county"]}, {week["place"]["state_name"]}'),
        "week_date": nice_date(week["date"]),
        "stories": "\n".join(story_block(st, apps_by_id) for st in stories),
        "live_panel": hero.panel(week, stories, nice_date, barn_href),
        "week_cards": "\n".join(stat_card(a, week["cards"].get(a["id"]), week) for a in apps if a["id"] in WEEKLY),
        "footer_contact": (f'      <a href="mailto:{e(config.EMAIL)}">Contact</a>' if config.EMAIL else ""),
        "robots": "" if config.PUBLIC else '<meta name="robots" content="noindex">',
    }
    layout = Template((TEMPLATES / "layout.html").read_text(encoding="utf-8"))

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(STATIC, OUT)
    def write(out_name, body, title, description, current=None):
        page = layout.substitute(
            values, body=body,
            title=e(f"{title} | {config.NAME}" if title else f"{config.NAME}: {config.TAGLINE}"),
            description=e(description),
            canonical=e(config.SITE_URL + ("" if out_name == "index.html" else out_name)),
            **{f"nav_{n}": (' aria-current="page"' if current == n else "") for n in ("barns", "about", "methods", "privacy")},
            nav_apps=(' data-current' if current == "apps" else ""),
        )
        (OUT / out_name).write_text(versioned(page), encoding="utf-8")

    for out_name, template, title, description, current in PAGES:
        body = Template((TEMPLATES / template).read_text(encoding="utf-8")).substitute(values)
        write(out_name, body, title, description, current)
    app_template = Template((TEMPLATES / "app.html").read_text(encoding="utf-8"))
    for app in apps:
        v = app_page_values(app, copy[app["id"]], week, weeks)
        own = [st for st in stories if st["app"] == app["id"]]
        v["stories"] = ("    <h2>What the Numbers Show</h2>\n" + "\n".join(
            story_block(st, apps_by_id, heading="h3", link=False) for st in own)) if own else ""
        card = week["cards"].get(app["id"])
        lead = f' This week, {week["place"]["county"]}, {week["place"]["state_name"]}: {card["headline"]}.' if card else ""
        write(APP_PAGE.format(app["id"]), app_template.substitute(values, **v), app["name"],
              f'{app["name"]}: {copy[app["id"]]["question"]}{lead}', "apps")
    # The county picker's data: every county's tiles, drawn in advance (hero.panel_data).
    corn, days = cards.load_static(cards.CORN), cards.load_static(cards.EQUIP)
    picker = hero.panel_data(week, cards.all_counties(), {"corn": corn["cards"], "days": days["cards"]},
                             {"corn": "The Yield Predictor covers " + corn["not_covered"][:1].lower() + corn["not_covered"][1:],
                              "days": "The Equipment Planner covers " + days["not_covered"][:1].lower() + days["not_covered"][1:]},
                             cards.STATE_NAMES, barn_href)
    (OUT / "panel-data.json").write_text(json.dumps(picker, separators=(",", ":")), encoding="utf-8")
    # One page per sale barn, and the index of them all
    for slug, barn in all_barns.items():
        title, desc, body = barn_pages.barn_page(slug, barn, all_barns, barn_data, nice_date)
        write(barn_pages.page_name(slug, barn), body, title, desc, "barns")
    write("barns.html", barn_pages.index_page(all_barns, nice_date), "Sale Barn Prices",
          "Feeder cattle prices at each sale barn Herd Planner follows, updated every Friday from USDA auction reports.",
          "barns")
    listed_barns = ["barns.html"] + [barn_pages.page_name(s, b) for s, b in all_barns.items()]

    listed = [p[0] for p in PAGES if p[0] != "404.html"] + [APP_PAGE.format(a["id"]) for a in apps] + listed_barns
    (OUT / "sitemap.xml").write_text(sitemap(listed, week["date"]), encoding="utf-8")
    # GitHub Pages runs pages through Jekyll unless this file exists; we don't need it.
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    # The custom domain. GitHub adds docs/CNAME when the domain is saved in Settings > Pages, but this
    # build empties docs/ every time (the Friday job too), so the build writes it back itself.
    if getattr(config, "DOMAIN", None):
        (OUT / "CNAME").write_text(config.DOMAIN + "\n", encoding="utf-8")
    if config.PUBLIC:
        robots = f"User-agent: *\nAllow: /\nSitemap: {config.SITE_URL}sitemap.xml\n"
    else:
        robots = "User-agent: *\nDisallow: /\n"
    (OUT / "robots.txt").write_text(robots, encoding="utf-8")
    return OUT


if __name__ == "__main__":
    out = build()
    print(f"Built {len(PAGES) + len(load_apps()) + 1 + len(cards.load_barns()['barns'])} pages for {config.NAME} into {out}")
