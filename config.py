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

# Ask search engines not to list the site until it lives at its own domain
# (cornerpostlogic.com). Set to True together with SITE_URL when the domain is pointed here.
PUBLIC = False

# The site's public address, ending in a slash: used for the sitemap and canonical links.
# Change it when the site moves to the company domain.
SITE_URL = "https://schirko.github.io/company-site/"

# Where "Sign In" in the menu goes: the suite's account service (farm-account), where each
# person's home page shows every app with their county's numbers. Change it with the domain.
ACCOUNT_URL = "https://farm-account.onrender.com/app/#signin"

# The year in the copyright line.
YEAR = 2026
