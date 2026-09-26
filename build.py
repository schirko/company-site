"""Build the company website into docs/, ready for GitHub Pages.

    python build.py

Why a build step at all, for a five-page site? Two things would otherwise be typed
by hand on every page and drift apart:

- the company name, which isn't chosen yet (it lives in config.py), and
- the list of apps, which already lives in static/suite/suite-apps.json, the same
  file the three apps' "Farm apps" menus read.

So pages are written once in templates/ with ${placeholders}, and this script fills
them in. It uses only Python's standard library (string.Template), so there is
nothing to install. GitHub Pages then serves the docs/ folder as it is.
"""

import html
import json
import shutil
from pathlib import Path
from string import Template

import config

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
OUT = ROOT / "docs"

HERD_PLANNER_TERMS = "https://herd-planner.onrender.com/app/terms.html"

# Each page: output file, template, <title> suffix, description, and which nav link is current.
PAGES = [
    ("index.html", "index.html", None, "Decision tools for ranchers and farmers: herd, crop and machinery decisions from your own records and public data.", None),
    ("about.html", "about.html", "About", "Who builds the apps, and how.", "about"),
    ("methods.html", "methods.html", "How we test", "How each app's models are tested, the results, and where each one falls short.", "methods"),
    ("privacy.html", "privacy.html", "Privacy", "How the apps handle your email and your records.", "privacy"),
    ("404.html", "404.html", "Page not found", "That page isn't here.", None),
]


def load_apps():
    return json.loads((STATIC / "suite" / "suite-apps.json").read_text(encoding="utf-8"))["apps"]


def e(text):
    """Escape text for HTML: an app name with an '&' in it must not break the page."""
    return html.escape(text, quote=True)


def app_card(app):
    link = (f'<a class="btn small" href="{e(app["url"])}">Open {e(app["name"])}</a>' if app["url"]
            else '<span class="status">Coming soon</span>')
    return f"""      <div class="card app-card">
        <img src="suite/suite-logos/{e(app["id"])}.svg" alt="" width="64" height="64">
        <h3>{e(app["name"])}</h3>
        <p>{e(app["what"])}.</p>
        {link}
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


def contact_sentence():
    if config.EMAIL:
        return f'Write to us at <a href="mailto:{e(config.EMAIL)}">{e(config.EMAIL)}</a>.'
    return "To reach us, use the Tell us button in Herd Planner. It comes straight to us."


def build():
    apps = load_apps()
    herd = next(a for a in apps if a["id"] == "herd-planner")
    values = {
        "name": e(config.NAME),
        "tagline": e(config.TAGLINE),
        "location": e(config.LOCATION),
        "year": str(config.YEAR),
        "herd_url": e(herd["url"] or "#apps"),
        "app_cards": "\n".join(app_card(a) for a in apps),
        "app_list": "\n".join(app_line(a) for a in apps),
        "terms_list": "\n".join(terms_line(a) for a in apps),
        "contact_sentence": contact_sentence(),
        "footer_apps": "\n".join(
            f'      <a href="{e(a["url"])}">{e(a["name"])}</a>' if a["url"]
            else f'      <span>{e(a["name"])} <small>(coming soon)</small></span>' for a in apps),
        "footer_contact": (f'      <a href="mailto:{e(config.EMAIL)}">Contact</a>' if config.EMAIL else ""),
        "robots": "" if config.PUBLIC else '<meta name="robots" content="noindex">',
    }
    layout = Template((TEMPLATES / "layout.html").read_text(encoding="utf-8"))

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(STATIC, OUT)
    for out_name, template, title, description, current in PAGES:
        body = Template((TEMPLATES / template).read_text(encoding="utf-8")).substitute(values)
        page = layout.substitute(
            values, body=body,
            title=e(f"{title} | {config.NAME}" if title else f"{config.NAME}: {config.TAGLINE}"),
            description=e(description),
            **{f"nav_{n}": (' aria-current="page"' if current == n else "") for n in ("apps", "about", "methods", "privacy")},
        )
        (OUT / out_name).write_text(page, encoding="utf-8")
    # GitHub Pages runs pages through Jekyll unless this file exists; we don't need it.
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    if not config.PUBLIC:
        (OUT / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    return OUT


if __name__ == "__main__":
    out = build()
    print(f"Built {len(PAGES)} pages for {config.NAME} into {out}")
