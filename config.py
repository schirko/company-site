"""Everything about the company that the site prints, in one place.

Change NAME (and TAGLINE if you like), run `python build.py`, and every page
updates. Nothing else in the site spells the name out. The name must match
"company" in static/suite/suite-apps.json (a test checks).
"""

# The company name (chosen 2026-09-27; domain cornerpostlogic.com).
NAME = "Cornerpost Logic"

# One line under the name on the home page.
TAGLINE = "Decision Tools for Ranchers and Farmers"

# Where the company is based (About page and footer).
LOCATION = "Centennial, Colorado"

# Contact address shown on the site (footer, About, Privacy). The company's shared address since 2026-10-30
# (Scott: "cornerpostlogic now has two email accounts - scott & contact"). Never a person's address here:
# the site is public, and a test allows no other address on any page.
EMAIL = "contact@cornerpostlogic.com"

# Search engines. False (for now, Scott's choice, 2026-09-27): every page says "noindex" and robots.txt
# disallows everything, so the site isn't listed or found by searching, though anyone given the
# address can still open it (GitHub Pages can't require a password). True invites search engines
# in (robots.txt points them at sitemap.xml) at launch.
PUBLIC = False

# The site's own domain (GitHub Pages "custom domain"). build.py writes it to docs/CNAME on
# every build: GitHub Pages reads that file, and without it the site falls back to github.io.
DOMAIN = "cornerpostlogic.com"

# The site's public address, ending in a slash: used for the sitemap and canonical links.
SITE_URL = f"https://{DOMAIN}/"

# Where "Sign In" in the menu goes: the suite's account service (farm-account), where each
# person's home page shows every app with their county's numbers. Change it with the domain.
# On the page of an app that has sign-up links ("signup" in content/apps.json) Sign In goes to that app's own
# sign-in card instead: a Herd Planner account is not a Your Account sign-in.
ACCOUNT_URL = "https://apps.cornerpostlogic.com/app/#signin"   # My Farm; farm-account.onrender.com until 2026-10-12
# 2026-10-20: My Farm's own address, where a barn page reads its notice and a barn sends Update This Page (barn_pages.py)
ACCOUNT_ORIGIN = "https://apps.cornerpostlogic.com"

# Subscription prices on the home page's app tiles ("From $12/mo", from "price_from" in content/apps.json).
# False until billing exists (the pilot shows no prices). Until then no link on the site says "Subscribe"
# either: that word only ever goes to a pay page (see "Sign-up links" in the README).
SHOW_PRICES = False

# The photo behind the home page's headline: a file under static/ (about 2,000 px wide, under 400 KB), and its
# credit line, which is printed on the photo. Scott picks the photos; nothing goes on the site unless he has
# chosen it and its license allows it. USDA ARS photos ask for "Photo courtesy of USDA ARS" (or with the
# photographer's name), and nothing may imply USDA endorses the apps. No file there: a plain green band.
HERO_PHOTO = "photos/hero.jpg"
HERO_CREDIT = "Photo courtesy of USDA ARS"

# The year in the copyright line.
YEAR = 2026

# Street View inside the barn pages' map box (2026-10-25, Scott chose A of notes/street-view-in-page-2026-10-25.png):
# Google's Maps Embed API key. It is a browser key, so it ends up in the built pages in docs/ (Google designs it to
# be seen; what protects it is its limits in Google Cloud: only cornerpostlogic.com, www., apps. and
# farm-account.onrender.com, and only the Maps Embed API). It is never written in this file: build.py reads it from
# the CORNERPOST_GOOGLE_EMBED_KEY setting (the weekly job's GitHub secret) or from google_embed_key.txt beside this
# file (Git-ignored; your PC). With neither, Street View opens in a smaller window as before.
def google_embed_key() -> str:
    import os
    from pathlib import Path
    key = os.environ.get("CORNERPOST_GOOGLE_EMBED_KEY", "").strip()
    if not key:
        f = Path(__file__).with_name("google_embed_key.txt")
        key = f.read_text(encoding="utf-8").strip() if f.exists() else ""
    return key
