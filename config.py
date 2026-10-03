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

# Contact address shown on the site. Left empty until there's a company address;
# the site then points people to each app's "Tell us" button instead. Don't put a
# personal address here: the site is public.
EMAIL = ""

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
ACCOUNT_URL = "https://farm-account.onrender.com/app/#signin"

# Plan prices on the home page's app tiles ("Plan from $12/mo", from "price_from" in content/apps.json).
# False until billing exists (the pilot shows no prices); the tiles then just say "Free to try".
SHOW_PRICES = False

# The photo behind the home page's headline: a file under static/ (about 2,000 px wide, under 400 KB), and its
# credit line, which is printed on the photo. Scott picks the photos; nothing goes on the site unless he has
# chosen it and its license allows it. USDA ARS photos ask for "Photo courtesy of USDA ARS" (or with the
# photographer's name), and nothing may imply USDA endorses the apps. No file there: a plain green band.
HERO_PHOTO = "photos/hero.jpg"
HERO_CREDIT = "Photo courtesy of USDA ARS"

# The year in the copyright line.
YEAR = 2026
