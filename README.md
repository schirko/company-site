# Company website

The front door for the farm apps: Herd Planner, the Yield Predictor and the
Farm Equipment Planner. A few plain pages (home, a page per app, About, How We Test, Privacy), built by a
small Python script and served free by GitHub Pages.

Every Friday the site picks a farm county and shows one real number from each app for it: this week's
550 lb steer price at the nearest sale barn, the county's trend corn yield, and its fall field days.
Each app page keeps a table of recent weeks, so the site gets new content every week on its own.

The company name isn't chosen yet, so the site says **Placeholder Ag** and asks search
engines not to list it. When the name is settled, change it in `config.py`, set
`PUBLIC = True`, rebuild, and push.

## How it's put together

```
company-site/
├── config.py          the company name, tagline, location, contact address, PUBLIC switch, SITE_URL
├── build.py           fills in the templates and writes the finished site to docs/ (plus sitemap.xml)
├── cards.py           the weekly stat cards: this week's county, the steer price, the history
├── templates/         the pages, with ${placeholders} for the name and the app list
├── content/apps.json  the home page's longer words about each app (tiles and app sections)
├── content/cards/     the county card files from the Yield Predictor and Equipment Planner,
│                      and weeks.json (every week shown so far, newest first)
├── .github/workflows/ weekly-cards.yml: the Friday refresh
├── static/            site.css, favicon.svg, and suite/ (the shared look and the app list)
├── docs/              the finished site: GitHub Pages serves this folder as it is
└── tests/             checks that every page builds and no link points nowhere
```

`static/suite/` holds copies of three files whose master copies live in
`herd-planner/brand/`: `suite.css` (the shared look), `suite.js` (the Farm apps menu)
and `suite-apps.json` (the list of apps). The home page's app cards and the footer
are built from that same list, so an app going live is still a one-file change.

## Build and check it

```powershell
cd B:\_Dev\Python\farm-apps\company-site
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python build.py
pytest
python -m http.server 8080 --directory docs
```

Then open http://127.0.0.1:8080 in a browser.

## The weekly stat cards

A GitHub Action (`.github/workflows/weekly-cards.yml`) runs every Friday morning: tests, then
`python cards.py refresh` (picks the county, asks Herd Planner's public `/suite/summary` for the steer
price, waiting up to about 4 minutes for it to wake), then `python build.py`, then commits and pushes.
Run it by hand from GitHub: **Actions > Weekly stat cards > Run workflow**. Because it pushes, pull
before you start work: `git pull`.

- **The county of the week** rotates through the 88 counties both county apps cover, in a fixed
  shuffled order, so each comes around about every 21 months.
- **No price that week** (Herd Planner asleep too long, or only sample prices): the card says so; the
  corn and field-day cards still show. Sample prices are never published.
- **New yields or weather:** export the cards in those projects (`python scripts\export_suite_card.py`
  in crop-yield-predictor, `python -m calculators.suite_card` in farm-equipment-planner), then here
  `python cards.py refresh` copies the new files into `content/cards/`. Commit and push them.
- A number shown for a week is saved in `content/cards/weeks.json` and never changes afterwards.

Search engines only see this once `PUBLIC = True` in `config.py` (it switches off `noindex` and points
`robots.txt` at `sitemap.xml`). Set `SITE_URL` to the company domain when the site moves.

## Put it online (free)

1. Create a GitHub repository for it and push this folder.
2. On GitHub: **Settings > Pages > Build and deployment**, Source **Deploy from a branch**,
   branch **master**, folder **/docs**, then **Save**.
3. After a minute the site is at `https://<your-username>.github.io/<repository-name>/`.

When there's a domain, the same Pages settings page has a **Custom domain** box.
