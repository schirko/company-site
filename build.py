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


# Each app's own page on this site, named by app id: templates/app.html, or templates/app_full.html for an
# app whose entry in content/apps.json has a "page" block (the fuller page; see full_page_values).
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
            groups.append(f'        <div class="mega-op">\n          <div class="mega-op-head"><p class="mega-op-title">{e(title)}</p>'
                          f'<p class="mega-op-lead">{e(lead)}</p></div>\n{links}\n        </div>')
    return "\n".join([
        '<details class="mega" data-mega>',
        '      <summary>Our Farm Apps</summary>',
        '      <div class="mega-panel">',
        *groups,
        '        <div class="mega-more">',
        '          <div><p class="mega-head">This week&#8217;s numbers</p>',
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


# How a new person gets into an app today: "signup" in content/apps.json (Scott, 2026-10-05: "we need to be subtly
# aggressive in having subscribe/sign up links to the products"). Two words, two meanings, and the site never
# mixes them: "Sign Up" / "Try for Free" makes a free account; "Subscribe" pays, so it waits for a pay page.
#   waitlist  the app is invite-only: every link reads Join the Waitlist and opens the app's waitlist card
#   open      anyone can make an account: Sign Up Free (cards: Try for Free)
# One setting per app flips every link. Change it the same day the app's own sign-up setting changes.
SIGNUP = {
    "waitlist": {"button": "Join the Waitlist", "nav": "Join the Waitlist", "nav_short": "Waitlist",
                 "tile": "Join the Waitlist", "panel": "Join the Waitlist", "hash": "#waitlist", "have_hash": ""},
    "open": {"button": "Sign Up Free", "nav": "Sign Up", "nav_short": "Sign Up", "tile": "Try for Free",
             "panel": "Try It Free for 30 Days", "hash": "#signup", "have_hash": "#signin"},
}


def signup(app, copy):
    """How a new person gets into this app today, or None: an app with no address or no "signup" setting gets
    no sign-up links anywhere. The addresses end in #waitlist, #signup and #signin, which the app reads to open
    the right card on its first screen."""
    state = copy.get("signup")
    if not state or not app.get("url"):
        return None
    if state not in SIGNUP:
        raise SystemExit(f'{app["id"]}: "signup" in content/apps.json must be one of {", ".join(SIGNUP)}, not "{state}".')
    if "?" in app["url"] or "#" in app["url"]:
        raise SystemExit(f'{app["id"]}: its address in suite-apps.json must be a plain one to hang #waitlist on, not {app["url"]}')
    base = app["url"].rstrip("/") + "/"
    words = SIGNUP[state]
    # "have": where "Have an invite or an account?" leads. On the waitlist that is the whole first screen (an
    # invite needs the account form, an account the sign-in card); with sign-up open, the sign-in card.
    return {**words, "state": state, "url": base + words["hash"], "signin": base + "#signin", "app": base,
            "have": base + words["have_hash"]}


def visitor(app, classes=""):
    """Attributes for a link only a new visitor needs: hidden in a browser that has used this app (member.js)."""
    return f'class="{(classes + " visitor-only").strip()}" data-app="{e(app["id"])}"'


def member(app, classes=""):
    """Attributes for what a browser that has used this app sees instead."""
    return f'class="{(classes + " member-only").strip()}" data-app="{e(app["id"])}"'


def member_apps(apps, copy):
    """The apps whose links back to this site say "this browser is signed in" (the ones with sign-up links)."""
    return [a for a in apps if signup(a, copy[a["id"]])]


def member_css(apps, copy):
    """Two rules per app: a browser that has used it loses that app's sign-up links and gains its Open link.
    In the page's head, so nothing flashes: member.js sets data-uses on <html> before the page is drawn."""
    return "\n".join(
        f'    html[data-uses="{a["id"]}"] .visitor-only[data-app="{a["id"]}"], '
        f'html:not([data-uses="{a["id"]}"]) .member-only[data-app="{a["id"]}"] {{ display: none !important; }}'
        for a in member_apps(apps, copy))


def nav_account(apps, copy, page_app=None):
    """The end of the header menu. Everywhere: Sign In (the suite account). On the page of an app with sign-up
    links: Sign In goes to that app, with its sign-up button beside it. And for each such app, the link a
    browser that has used it sees instead of both ("Open Herd Planner"): the site can't see an app's sign-in
    (different domains), so it remembers the browser, and the words stay true signed in or not."""
    su = signup(page_app, copy[page_app["id"]]) if page_app else None
    parts = [f'<a class="nav-signin nav-visitor" href="{e(su["signin"] if su else config.ACCOUNT_URL)}">Sign In</a>']
    if su:
        parts.append(f'<a {visitor(page_app, "nav-signup")} href="{e(su["url"])}"><span class="wide">{e(su["nav"])}</span>'
                     f'<span class="narrow">{e(su["nav_short"])}</span></a>')
    for a in member_apps(apps, copy):
        short = copy[a["id"]].get("member_short", "Open")
        parts.append(f'<a {member(a, "nav-signin nav-member")} href="{e(a["url"])}"><span class="wide">Open {e(a["name"])} &#8594;</span>'
                     f'<span class="narrow">{e(short)} &#8594;</span></a>')
    return "\n      ".join(parts)


SEASON_OF = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
             6: "summer", 7: "summer", 8: "summer", 9: "fall", 10: "fall", 11: "fall"}


def season_of(day) -> str:
    """ "2026-10-02" (or a date) -> "fall". Seasons by whole months, December to February being winter."""
    try:
        month = day.month if hasattr(day, "month") else date.fromisoformat(str(day)).month
    except ValueError:
        raise SystemExit(f'The date being published must read like 2026-10-02, not "{day}".') from None
    return SEASON_OF[month]


def check_page(app, copy):
    """Stop the build with a plain sentence when a fuller page's words are incomplete, rather than a KeyError
    on some Friday (a season's panel is first read on the first build of that season)."""
    page, name = copy["page"], app["id"]
    def need(block, keys, where):
        missing = [k for k in keys if not block.get(k)]
        if missing:
            raise SystemExit(f'{name}: {where} in content/apps.json needs {", ".join(missing)}.')
    if signup(app, copy):
        need(page, ["signup"], '"page"')
        need(page["signup"], ["ask", "member_fine", copy["signup"]], '"page" > "signup"')
        need(page["signup"][copy["signup"]], ["fine", "have", "have_link", "close_title", "close"],
             f'"page" > "signup" > "{copy["signup"]}"')
    panels = [("panel", page["panel"])] if page.get("panel") else []
    if page.get("year"):
        need(page["year"], ["title", "note", "more", "seasons"], '"page" > "year"')
        for s in page["year"]["seasons"]:
            need(s, ["id", "name", "title", "text"], f'a season in "page" > "year"')
            if s.get("panel"):
                panels.append((f'the {s["id"]} panel', s["panel"]))
    for where, panel in panels:
        need(panel, ["title", "text", "picture"], where)
        if panel["picture"] not in ("showcase", "sample"):
            raise SystemExit(f'{name}: a panel\'s "picture" must be "showcase" or "sample", not "{panel["picture"]}" ({where}).')
        if panel["picture"] == "sample" and not page.get("sample"):
            raise SystemExit(f'{name}: {where} shows the sample, but the page has no "sample".')


def app_tile(app, copy, week):
    """A big tile in the opening row. Top right: this week's number from the app (tile_stat). The name and
    question lead to the app's page on this site; at the bottom, Open (into the app) and one way in for someone
    new: the app's sign-up link (signup(): Join the Waitlist or Try for Free), or for an app with none, what is
    true of it ("tile_note": Free, no account). No Subscribe link here (Scott, 2026-10-05: "just Open and Try
    for Free"); that word waits for a pay page. The starting price shows once billing exists (config.SHOW_PRICES).
    While an app is invite-only, a line above the buttons says what a new person can count on today
    ("tile_waitlist": Free account. By invite for now.): Scott, 2026-10-07, "From the card it looks like you have
    to pay". Like the link, it is for visitors only, and it goes when sign-up opens (the link then says Try for Free)."""
    stat = tile_stat(app["id"], week)
    stat_html = ""
    if stat:
        number, unit, small, tone = stat
        detail = week["cards"][app["id"]]["detail"]
        stat_html = (f'<span class="tile-stat" title="{e(detail)}"><span class="tile-number">'
                     f'<b class="{tone}">{e(number)}</b>{e(unit)}</span><small>{e(small)}</small></span>')
    inner = f"""<span class="tile-top"><img src="suite/suite-logos/{e(app["id"])}.svg" alt="" width="56" height="56">{stat_html}</span>
        <span class="tile-words"><strong>{e(app["name"])}</strong><span>{e(copy["question"])}</span></span>"""
    price = (f'From <b>{e(copy["price_from"])}/mo</b>' if config.SHOW_PRICES and copy.get("price_from") else "")
    if app["url"]:
        su = signup(app, copy)
        line = ""
        if su and su["state"] == "waitlist" and copy.get("tile_waitlist"):
            line = f'\n        <span {visitor(app, "tile-free")}>{e(copy["tile_waitlist"])}</span>'
        if su:
            way_in = f'<a {visitor(app, "tile-link")} href="{e(su["url"])}">{e(su["tile"])}</a>'
            way_in += f'<span class="tile-price">{price}</span>' if price else ""
        else:
            way_in = f'<span class="tile-price">{e(copy.get("tile_note", "Free to try"))}{"<br>" + price if price else ""}</span>'
        return f"""      <div class="tile tile-app">
        <a class="tile-body" href="{APP_PAGE.format(e(app["id"]))}">{inner}</a>{line}
        <span class="tile-bottom"><a class="btn small" href="{e(app["url"])}" aria-label="Open {e(app["name"])}">Open</a>{way_in}</span>
      </div>"""
    later = f'<span class="tile-price">{price}</span>' if price else ""
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
        # Herd Planner's saved label says "this week"; the card names the sale's day instead (hero.steer_label),
        # which stays true when the card is shown again under Recent Weeks.
        label = hero.steer_label(card) if app["id"] == "herd-planner" and card.get("as_of") else card["label"]
        inner = f"""<span class="stat-label">{e(label)}</span>
        <span class="stat-headline">{e(card["headline"])}</span>
        <span class="stat-detail">{e(card["detail"])}</span>
        <span class="stat-source">{foot}</span>"""
    else:
        inner = f"""<span class="stat-label">{e(hero.steer_label(None))}</span>
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


def herd_week_card(card, week, barn, href):
    """Herd Planner's This Week card (option C, Scott 2026-09-30): the 550 lb steer price at the barn with its 8-in-10
    band, then "sell now or wait?": that barn's steer-calf months against an average month, this month marked.
    Falls back to the plain stat card when there's no price or no season pattern."""
    season = next((x for x in (barn or {}).get("seasons") or [] if x.get("key") == "calves"), None)
    if not card or not season:
        return None
    sold = date.fromisoformat(card["as_of"])
    m = date.fromisoformat(week["date"]).month
    typical = {t["month"]: t["index"] for t in season["typical"]}
    index = [typical.get(i, 1.0) for i in range(1, 13)]
    pct = lambda month: (typical[month] - 1) * 100
    def words(month):
        v = pct(month)
        return "about the same as an average month" if abs(v) < 1 else f"about {abs(v):.0f}% {'above' if v > 0 else 'below'} an average month"
    best, worst = charts.MONTH_NAMES[season["best"] - 1], charts.MONTH_NAMES[season["worst"] - 1]
    now = charts.MONTH_NAMES[m - 1]
    band = hero.range_bar(card["low"], card["value"], card["high"], card["low"] * 0.97, card["high"] * 1.03,
                          (hero.money(card["low"]), "", hero.money(card["high"])), marker="this sale")
    lean = "" if season.get("clear", True) else " (a lean, not a rule: the gap is within the year-to-year noise)"
    link = f'<a class="week-link" href="{e(href)}">See {e(barn["name"])}&#8217;s full price sheet</a>' if href else ""
    return f"""      <div class="stat-card week-card">
        <span class="stat-label">550 lb steer &middot; {e(card["market"])} &middot; sale of {sold:%b} {sold.day}</span>
        <span class="week-price">{hero.money(card["value"])}<small>/cwt</small></span>
        <span class="week-sub">about <b>{hero.money(card["value"] * 5.5)}</b> a head &middot; 8 in 10 sales {hero.money(card["low"])} to {hero.money(card["high"])}</span>
        {band}
        <div class="week-split">
          <span class="stat-label">Sell now or wait? Steer calves by month</span>
          {hero.month_strip(index, m - 1)}
          <span class="stat-detail"><b>Now ({now}):</b> {words(m)}. <b>{best}</b> typically runs {words(season["best"])},
            <b>{worst}</b> {words(season["worst"])}{lean}. Waiting also means feed and gain: Herd Planner weighs both for each calf.</span>
        </div>
        <span class="stat-source">Source: {e(card["source"])}; the months from USDA reports since 2021, with the market&#8217;s rise taken out.</span>
        {link}
      </div>"""


def price_sheet_svg(prices) -> str:
    """Steers and heifers, 400 to 800 lb, at one barn this week: a pale band for where 8 in 10 sales land and a dot
    at the model's price, 550 lb steers in full color. Dots on a shared $ scale, not bars from a cut-off axis
    (bars that start at $300 would make a $400 calf look twice a $350 one)."""
    w, row, left, right = 320, 22, 64, 52
    lo = min(p["low"] for p in prices) - 10
    hi = max(p["high"] for p in prices) + 10
    x = lambda v: left + (v - lo) / (hi - lo) * (w - left - right)
    out, y = [], 0
    for cls in ("Steers", "Heifers"):
        rows = sorted((p for p in prices if p["animal_class"] == cls), key=lambda p: p["weight_lb"])
        if not rows:
            continue
        y += 16
        out.append(f'<text x="0" y="{y}" class="tick strong">{cls}</text>')
        for p in rows:
            y += row
            key = cls == "Steers" and p["weight_lb"] == 550
            out.append(f'<text x="0" y="{y + 4}" class="tick">{p["weight_lb"]} lb</text>')
            out.append(f'<rect x="{x(p["low"]):.1f}" y="{y - 4}" width="{x(p["high"]) - x(p["low"]):.1f}" height="8" rx="2" '
                       f'fill="{hero.BLUE_LIGHT}"/>')
            out.append(f'<circle cx="{x(p["price"]):.1f}" cy="{y}" r="{5 if key else 4}" fill="{hero.BLUE if key else "#5e5c57"}"/>')
            out.append(f'<text x="{w}" y="{y + 4}" text-anchor="end" class="tick{" strong" if key else ""}">'
                       f'{hero.money(p["price"])}</text>')
        y += 6
    return f'<svg class="mini sheet" viewBox="0 0 {w} {y + 4}" aria-hidden="true">{"".join(out)}</svg>'


def price_sheet_card(barn, href):
    """Slide 2 of Herd Planner's This Week: the barn's whole price sheet this week, with a table for screen readers."""
    last = (barn or {}).get("weeks", [])[-1:] or None
    if not last or not last[0].get("prices") or not last[0].get("fresh", True):
        return None
    wk = last[0]
    sold = date.fromisoformat(wk["last_sale"]) if wk.get("last_sale") else None
    rows = "".join(f'<tr><td>{e(p["animal_class"])}</td><td>{p["weight_lb"]} lb</td><td>{hero.money(p["price"])}</td>'
                   f'<td>{hero.money(p["low"])} to {hero.money(p["high"])}</td></tr>' for p in wk["prices"])
    link = f'<a class="week-link" href="{e(href)}">Open {e(barn["name"])}&#8217;s page</a>' if href else ""
    return f"""      <div class="stat-card week-card">
        <span class="stat-label">The whole price sheet &middot; {e(barn["name"])}{f" &middot; sale of {sold:%b} {sold.day}" if sold else ""} &middot; $/cwt</span>
        {price_sheet_svg(wk["prices"])}
        <span class="stat-detail">Dots: the price for that weight. Pale bands: where 8 in 10 sales land. Lighter calves bring more a
          pound; heifers run under steers of the same weight.</span>
        <details class="sheet-numbers"><summary>Show the numbers</summary>
          <table><thead><tr><th>Class</th><th>Weight</th><th>Price</th><th>8 in 10 sales</th></tr></thead><tbody>{rows}</tbody></table>
        </details>
        {link}
      </div>"""


def week_slider(slides: list[str]) -> str:
    """This Week's cards side by side in a row you swipe or step through with arrows (slider.js), with dots that say
    which card is showing. One card: no slider at all."""
    if len(slides) == 1:
        return slides[0]
    items = "\n".join(f'        <div class="week-slide" role="group" aria-roledescription="slide" aria-label="{i + 1} of {len(slides)}">\n{s}\n        </div>'
                      for i, s in enumerate(slides))
    return f"""      <div class="slider week-slider" data-slider data-dots>
        <div class="tiles" role="region" aria-label="This week, card by card" tabindex="0">
{items}
        </div>
        <button class="slide-btn prev" type="button" aria-label="Previous card" hidden>&#8249;</button>
        <button class="slide-btn next" type="button" aria-label="Next card" hidden>&#8250;</button>
        <div class="slide-dots" aria-hidden="true"></div>
      </div>"""


def week_blocks(app, week, weeks, barns=None, barn_href=None):
    """This Week and Recent Weeks for an app in the Friday job; for other apps, how to get this season's
    numbers from the app itself."""
    if app["id"] not in WEEKLY:
        link = (f'<a href="{e(app["url"])}">Open {e(app["name"])}</a>' if app["url"] else e(app["name"]))
        return (f"""        <h2>This Season</h2>
        <p>Pick your county in the app: {link}. The forecasts update every Monday from April to November,
          as new satellite and weather data come in.</p>""", "")
    place = week["place"]
    raw = week["cards"].get(app["id"])
    card = None
    if app["id"] == cards.HERD and raw and barns:
        slug = str(raw.get("market_slug", ""))
        href = barn_href(slug) if barn_href else None
        slides = [c for c in (herd_week_card(raw, week, barns.get(slug), href), price_sheet_card(barns.get(slug), href)) if c]
        card = week_slider(slides) if slides else None
    card = card or stat_card(app, raw, week, link=False)
    history = history_table(app["id"], weeks)
    return (f"""        <h2>This Week: {e(f'{place["county"]}, {place["state_name"]}')}</h2>
{card}""", f"""    <h2>Recent Weeks</h2>
    <p class="section-lede">Each Friday we pick a farm county and add a line here. {e(HISTORY_NOTE[app["id"]])}</p>
{history}
""")


def app_page_values(app, copy, week, weeks, barns=None, barn_href=None):
    week_block, history_block = week_blocks(app, week, weeks, barns, barn_href)
    return {
        "app_id": e(app["id"]), "app_name": e(app["name"]), "question": e(copy["question"]),
        "audience": e(copy["audience"]), "note": e(copy["note"]),
        "points": "\n".join(f"          <li>{e(p)}</li>" for p in copy["points"]),
        "open_button": (f'<a class="btn" href="{e(app["url"])}">Open {e(app["name"])}</a>' if app["url"]
                        else '<span class="status">Coming soon</span>'),
        "week_block": week_block, "history_block": history_block,
        "method": e(APP_METHOD[app["id"]]), "source": e(APP_SOURCE[app["id"]]),
    }


def feature_panel(app, copy, su, season):
    """Beside the headline: one subscription job, with the app's own picture and the sign-up button (Scott,
    2026-10-05, of the white space there: "Maybe a Sign-up ad for us with a feature of the paid subscription?").
    Chosen from three mockups: the job changes with the season ("year" in apps.json; the build takes the season
    from the week it publishes). A season only takes over when it has a panel of its own, because a panel's words
    must describe its own picture; otherwise the page's standing panel shows. No "panel" at all: the picture alone."""
    page = copy["page"]
    seasons = {s["id"]: s for s in page.get("year", {}).get("seasons", [])}
    own = seasons.get(season, {}).get("panel")
    panel = own or page.get("panel")
    if not panel:
        return app_shot(app, copy)
    if panel["picture"] == "sample":
        sample = page["sample"]
        # The sample never appears without saying what it is: made-up cattle, and not an appraisal.
        picture = (f'<div class="lp-paper lp-paper-small"><img src="{e(sample["image"])}" alt="{e(sample["alt"])}" '
                   f'width="{int(sample["width"])}" height="{int(sample["height"])}"></div>\n'
                   f'        <p class="lp-feature-note">{e(sample["caption"])}</p>')
    else:
        picture = app_shot(app, copy)
    tag = f'This {e(seasons[season]["name"].lower())} &#183; with a subscription' if own else "With a subscription"
    button = f'<a {visitor(app, "btn ghost")} href="{e(su["url"])}">{e(su["panel"])}</a>' if su else ""
    more = (f'<a class="lp-feature-more" href="#year">{e(page["year"]["more"])} &#8594;</a>' if page.get("year") else "")
    return f"""<aside class="lp-feature">
        <span class="lp-tag">{tag}</span>
        <h2>{e(panel["title"])}</h2>
        <p>{e(panel["text"])}</p>
        {picture}
        <p class="lp-feature-cta">{button}{more}</p>
      </aside>"""


def year_strip(page, season):
    """What a subscription is for in each season (Scott, 2026-10-05: "features the farmer or rancher can use in
    the off season to encourage year-round subscriptions"). Every line is something the app does today; the
    season being published is marked."""
    year = page.get("year")
    if not year:
        return ""
    def card(s):
        cls, mark = (' class="now"', " <i>Now</i>") if s["id"] == season else ("", "")
        return (f'      <li{cls}><span class="lp-season">{e(s["name"])}{mark}</span>'
                f'<b>{e(s["title"])}</b><span>{e(s["text"])}</span></li>')
    cards_ = "\n".join(card(s) for s in year["seasons"])
    return f"""    <h2 id="year">{e(year["title"])}</h2>
    <p class="section-lede">{e(year["note"])}</p>
    <ol class="lp-year">
{cards_}
    </ol>"""


def full_page_values(app, copy, day=None):
    """The fuller page's own parts (templates/app_full.html), from the app's "page" block in content/apps.json:
    the headline, the sample cut off partway, what is free and what comes with a subscription, and the steps.
    Chosen by Scott from three mockups, 2026-10-05 (layout A, "the report first"). The words are all in
    apps.json, so another app gets the same page by filling in its own block; parts it leaves out are skipped.

    Sign-up links (2026-10-05): the main button, a line under the sample, under What You Get, and a closing
    band, all from signup() so one setting changes them together, plus the feature panel beside the headline
    and the year strip. `day` is the date being published (it picks the season); today when left out.

    Two rules the page keeps (tests hold both): it shows no price until billing exists (config.SHOW_PRICES),
    and the sample is a real page from the app with made-up cattle, cut off and labeled, never a blurred fake."""
    page = copy["page"]
    check_page(app, copy)
    season = season_of(day or date.today())
    su = signup(app, copy)
    words = page["signup"][su["state"]] if su else None
    join = f'<a {visitor(app, "btn")} href="{e(su["url"])}">{e(su["button"])}</a>' if su else ""

    def items(lines, pad="          "):
        return "\n".join(f"{pad}<li>{e(line)}</li>" for line in lines)

    sample, band, button = page.get("sample"), "", ""
    second = page.get("second_sample") if sample else None

    def paper(smp):
        """A page from the app, cut off by the styles: the picture, what the rest holds, and what it is."""
        if not (STATIC / smp["image"]).exists():
            raise SystemExit(f'{app["id"]}: the sample picture static/{smp["image"]} is missing.')
        return f"""<figure class="lp-peek">
        <div class="lp-paper"><img src="{e(smp["image"])}" alt="{e(smp["alt"])}" width="{int(smp["width"])}" height="{int(smp["height"])}" loading="lazy">
          <p class="lp-more">{e(smp["more"])}</p></div>
        <figcaption>{e(smp["caption"])}</figcaption>
      </figure>"""
    ask = (f'''
      <p {visitor(app, "lp-ask")}><span>{e(page["signup"]["ask"])}</span> <a class="btn" href="{e(su["url"])}">{e(su["button"])}</a></p>'''
           if su else "")
    if sample:
        button = f'<a class="btn ghost" href="#{e(sample["id"])}">{e(sample["button"])}</a>'
        band = f"""    <div class="lp-band" id="{e(sample["id"])}">
      <div class="lp-band-top">
        <div>
          <span class="lp-tag">{e(sample["tag"])}</span>
          <h2>{e(sample["title"])}</h2>
          <p>{e(sample["lead"])}</p>
        </div>
        <ul>
{items(sample["points"])}
        </ul>
      </div>
      {paper(sample)}{ask}
    </div>"""
    if second:
        # Two pages side by side (Scott chose this from three mockups, 2026-10-05): what a subscription makes for
        # the lender beside what the free records make for the buyer. On a phone they stack.
        def half(smp, free):
            return f"""<div class="lp-half" id="{e(smp["id"])}-page">
          <span class="lp-tag{" lp-tag-free" if free else ""}">{e(smp["tag"])}</span>
          <h3>{e(smp["title"])}</h3>
          <p>{e(smp["lead"])}</p>
          {paper(smp)}
        </div>"""
        band = f"""    <div class="lp-band" id="{e(sample["id"])}">
      <h2>{e(page["samples_title"])}</h2>
      <div class="lp-pair">
        {half(sample, False)}
        {half(second, True)}
      </div>{ask}
    </div>"""
    free = ""
    if page.get("free") and page.get("subscription"):
        lead, rest = page["trial"]
        lead = (words or {}).get("trial_lead", lead)   # beside a waitlist button the 30 days need "With an account"
        col_free = col_sub = trial_button = ""
        if su and su["state"] == "open":   # two ways in, each under its own list
            col_free = f'''
          <p {visitor(app, "lp-col-cta")}><a class="btn ghost" href="{e(su["url"])}">{e(su["button"])}</a></p>'''
            col_sub = f'''
          <p {visitor(app, "lp-col-cta")}><a class="btn" href="{e(su["url"])}">{e(su["panel"])}</a></p>'''
        elif su:                           # one list to join, so one button, beside the 30 days
            trial_button = f' <a {visitor(app, "btn")} href="{e(su["url"])}">{e(su["button"])}</a>'
        free = f"""    <div class="lp-band" id="what-you-get">
      <h2>{e(page["free_title"])}</h2>
      <div class="lp-two">
        <div class="lp-col">
          <h3>Free</h3>
          <p class="lp-when">{e(page["free_note"])}</p>
          <ul>
{items(page["free"], "            ")}
          </ul>{col_free}
        </div>
        <div class="lp-col lp-sub-col">
          <h3>With a Subscription</h3>
          <p class="lp-when">{e(page["subscription_note"])}</p>
          <ul>
{items(page["subscription"], "            ")}
          </ul>{col_sub}
        </div>
      </div>
      <p class="lp-trial{" lp-trial-cta" if trial_button else ""}"><span><strong>{e(lead)}</strong> {e(rest)}</span>{trial_button}</p>
    </div>"""
    steps = ""
    if page.get("steps"):
        rows = "\n".join(f"      <li><b>{e(title)}</b><span>{e(words)}</span></li>" for title, words in page["steps"])
        steps = f"""    <h2>How It Works</h2>
    <ol class="lp-steps">
{rows}
    </ol>"""
    # The top: for someone new, the way in; for a browser that has used the app, straight into it.
    opener = f'<a class="btn" href="{e(app["url"])}">Open {e(app["name"])}</a>' if app["url"] else '<span class="status">Coming soon</span>'
    fine, closing = (f'<p class="lp-fine">{e(page["offer"])}</p>' if page.get("offer") else ""), ""
    if su:
        opener = join + f'<a {member(app, "btn")} href="{e(app["url"])}">Open {e(app["name"])}</a>'
        have = f'{e(words["have"])} <a href="{e(su["have"])}">{e(words["have_link"])}</a>'
        fine = f"""<p {visitor(app, "lp-fine")}>{e(words["fine"])}</p>
        <p {visitor(app, "lp-have")}>{have}</p>
        <p {member(app, "lp-fine")}>{e(page["signup"]["member_fine"])} <a href="privacy.html#this-browser">Why?</a>
          <button type="button" class="linklike" data-forget-app>Forget this</button></p>"""
        closing = f"""    <div {visitor(app, "lp-close")}>
      <h2>{e(words["close_title"])}</h2>
      <p>{e(words["close"])}</p>
      <p class="lp-cta"><a class="btn" href="{e(su["url"])}">{e(su["button"])}</a></p>
      <p class="lp-have">{have}</p>
    </div>"""
    return {
        "headline": e(page["headline"]), "sub": e(page["sub"]), "fine": fine, "open_button": opener,
        "sample_button": button, "sample_band": band, "free_band": free, "steps_block": steps,
        "shot": feature_panel(app, copy, su, season), "year_strip": year_strip(page, season), "closing": closing,
        "weekly_title": e(page["weekly_title"]), "weekly_text": e(page["weekly_text"]), "weekly_note": e(page["weekly_note"]),
    }


def sitemap(pages, lastmod):
    urls = "\n".join(f"  <url><loc>{e(config.SITE_URL + ('' if p == 'index.html' else p))}</loc>"
                     f"<lastmod>{lastmod}</lastmod></url>" for p in pages)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "\n</urlset>\n")


# --- "Why Use Our Apps": one real finding per story, drawn by charts.py -------------------------


def load_stories():
    return json.loads((CONTENT / "stories.json").read_text(encoding="utf-8"))["stories"]


def story_block(story, apps_by_id, heading="h3", link=True, how=False):
    app = apps_by_id[story["app"]]
    # On the home page each finding leads two ways: to the app it came from, and to how that app is tested
    # (methods.html has a section per app, named by the app's id).
    more = (f'<p class="story-link"><a href="{APP_PAGE.format(e(app["id"]))}">More about {e(app["name"])}</a>'
            f' <span aria-hidden="true">&middot;</span> <a href="methods.html#{e(app["id"])}">How we test it</a></p>'
            if link else "")
    return f"""      <figure class="story" id="{e(story["id"])}">
        <p class="stat-app"><img src="suite/suite-logos/{e(app["id"])}.svg" alt="" width="24" height="24"> {e(app["name"])}</p>
        <{heading}>{e(story["title"])}</{heading}>
        <p class="story-headline">{e(story["headline"])}</p>
        <p class="chart-title">{e(story["chart_title"])}</p>
        {f'<p class="how-to-read"><strong>How to read it:</strong> {e(story["how_to_read"])}</p>' if how and story.get("how_to_read") else ""}
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


def hero_photo() -> tuple[str, str, str]:
    """(class, style attribute, credit line) for the top of the home page. The photo's address carries a short
    hash, like the stylesheets', so a replaced photo is never shown from a browser's old copy. A photo without
    a credit line stops the build: the credit is a condition of using it."""
    name = getattr(config, "HERO_PHOTO", "")
    if not name or not (STATIC / name).exists():
        return "", "", ""
    credit = getattr(config, "HERO_CREDIT", "").strip()
    if not credit:
        raise SystemExit(f"config.HERO_CREDIT is empty: {name} can't go on the site without its credit line.")
    tag = hashlib.sha256((STATIC / name).read_bytes()).hexdigest()[:10]
    return (" has-photo", f' style="background-image: url({e(name)}?v={tag})"',
            f'  <p class="photo-credit">{e(credit)}</p>')


VERSIONED = ("suite/suite.css", "site.css", "suite/suite.js", "slider.js", "panel.js", "menu.js", "member.js")


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
        "herd_url": e((signup(herd, copy[herd["id"]]) or {}).get("url") or herd["url"] or "#apps"),
        "app_tiles": "\n".join([app_tile(a, copy[a["id"]], week) for a in apps]
                               + [dev_tile(d) for d in copy.get("in_development", [])]),
        "account_url": e(config.ACCOUNT_URL),
        "member_css": member_css(apps, copy),
        "member_apps": e(" ".join(a["id"] for a in member_apps(apps, copy))),
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
        "pins": hero.pins(week, barn_href),
        **dict(zip(("hero_class", "hero_style", "hero_credit"), hero_photo())),
        "week_cards": "\n".join(stat_card(a, week["cards"].get(a["id"]), week) for a in apps if a["id"] in WEEKLY),
        "footer_contact": (f'      <a href="mailto:{e(config.EMAIL)}">Contact</a>' if config.EMAIL else ""),
        "robots": "" if config.PUBLIC else '<meta name="robots" content="noindex">',
    }
    layout = Template((TEMPLATES / "layout.html").read_text(encoding="utf-8"))

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(STATIC, OUT)
    def write(out_name, body, title, description, current=None, page_app=None):
        page_signup = bool(page_app and signup(page_app, copy[page_app["id"]]))
        page = layout.substitute(
            values, body=body,
            nav_account=nav_account(apps, copy, page_app), nav_class=(" has-signup" if page_signup else ""),
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
    full_template = Template((TEMPLATES / "app_full.html").read_text(encoding="utf-8"))
    for app in apps:
        v = app_page_values(app, copy[app["id"]], week, weeks, all_barns, barn_href)
        full = "page" in copy[app["id"]]
        if full:
            v.update(full_page_values(app, copy[app["id"]], week["date"]))
        own = [st for st in stories if st["app"] == app["id"]]
        # Smaller and explained (Scott, 2026-09-30): side by side on a computer, a one-line intro, and a "How to
        # read it" line on each chart (stories.json "how_to_read").
        v["stories"] = (f"""    <h2>What the Numbers Show</h2>
    <p class="section-lede">{"Findings from the work behind " + e(app["name"]) + ", each with its source and its limits." if len(own) > 1 else "A finding from the work behind " + e(app["name"]) + ", with its source and its limits."}</p>
    <div class="stories-compact{' pair' if len(own) > 1 else ''}">
""" + "\n".join(story_block(st, apps_by_id, heading="h3", link=False, how=True) for st in own) + "\n    </div>") if own else ""
        card = week["cards"].get(app["id"])
        lead = f' This week, {week["place"]["county"]}, {week["place"]["state_name"]}: {card["headline"]}.' if card else ""
        write(APP_PAGE.format(app["id"]), (full_template if full else app_template).substitute(values, **v), app["name"],
              f'{app["name"]}: {copy[app["id"]]["question"]}{lead}', "apps", page_app=app)
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
