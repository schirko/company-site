# Company website

The front door for the farm apps: Herd Planner, the Yield Predictor and the
Farm Equipment Planner. A few plain pages (home, a page per app, About, How We Test, Privacy), built by a
small Python script and served free by GitHub Pages.

Every Friday the site picks a farm county and shows one real number from each app for it: this week's
550 lb steer price at the nearest sale barn, the county's trend corn yield, and its fall field days.
Each app page keeps a table of recent weeks, so the site gets new content every week on its own.

The company is **Cornerpost Logic**, at **https://cornerpostlogic.com/** (bought at Namecheap
2026-09-27; GitHub Pages custom domain). `DOMAIN` in `config.py` is written to `docs/CNAME` on every
build, because GitHub Pages only serves the domain while that file names it (and `build.py` empties
`docs/` each time). The old github.io address redirects here. Not launched yet: `PUBLIC = False` keeps search
engines out ("noindex" on every page, a disallow-all robots.txt). Set it to True at launch.

DNS at Namecheap (Advanced DNS): four A records for `@` (185.199.108.153, .109.153, .110.153,
.111.153), four AAAA records for `@` (2606:50c0:8000::153 to 2606:50c0:8003::153), and a CNAME
`www` -> `schirko.github.io`. No wildcard records.

## How it's put together

```
company-site/
├── config.py          the company name, tagline, location, contact address, PUBLIC switch, SITE_URL,
│                      ACCOUNT_URL (where "Sign In" in the menu goes: farm-account)
├── build.py           fills in the templates and writes the finished site to docs/ (plus sitemap.xml)
├── cards.py           the weekly stat cards: this week's county, the steer price, the history
├── charts.py          draws the "Why Use Our Apps" charts as SVG, in plain Python
├── hero.py            the home page's live numbers: three pins on the photo, and the panel under it
├── barn_pages.py      one page per sale barn, and the Barn Prices index
├── static/panel.js    "See your county": swaps the pins and the panel's tiles to a visitor's county
├── static/slider.js   the app tiles row: arrow buttons for the sideways-scrolling row
├── static/menu.js     the header's Our Farm Apps menu: closes on a click elsewhere, Escape or a chosen link
├── templates/         the pages, with ${placeholders} for the name and the app list
├── content/apps.json  the home page's longer words about each app (tiles and app sections), and
│                      "in_development": apps being built (a tile with Get notified, nothing else)
├── content/stories.json  the "Why Use Our Apps" findings: numbers, words and sources
├── content/cards/     the county card files from the Yield Predictor and Equipment Planner,
│                      and weeks.json (every week shown so far, newest first)
├── .github/workflows/ weekly-cards.yml: the Friday refresh
├── static/            site.css, favicon.svg, soon/ (logos of apps in development), photos/hero.jpg
│                      (the photo behind the home page's headline) and suite/ (the shared look and
│                      the app list)
├── docs/              the finished site: GitHub Pages serves this folder as it is
└── tests/             checks that every page builds and no link points nowhere
```

`static/suite/` holds copies of three files whose master copies live in
`herd-planner/brand/`: `suite.css` (the shared look), `suite.js` (the Farm apps menu)
and `suite-apps.json` (the list of apps). The home page's app cards and the footer
are built from that same list, so an app going live is still a one-file change.

**The header's Our Farm Apps menu** (2026-09-30, option C of three mockups in `notes/mega-menu-mockups-2026-09-30.png`,
after Tractor Zoom's Solutions menu): a panel sorted by operation, **For Ranches** (Herd Planner, Grazing Planner)
and **For Farms** (Yield Predictor, Farm Equipment Planner), each app with its logo, its one line from
`suite-apps.json` and a link to its page here; then **This week's numbers** (Barn Prices, This week in your county),
**Why trust it** (How We Test), and a strip linking to Your Account. `build.mega_menu()` draws it; which group an
app belongs to is `OPERATIONS` in `build.py`, and a test fails if a live app isn't in exactly one group, so a new
app needs a line there too. It's a `<details>` element, so it opens without JavaScript; on an app's page its title is
underlined like the other current links. The header is now Our Farm Apps, Barn Prices, About, How We Test and
Sign In: Privacy moved to the footer only, and the separate Farm Apps grid menu is gone from this site (this menu
does its job; the apps keep theirs). Tablets put the free tools under the two operations; phones show one
scrolling column.

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

## The top of the home page: numbers on the land

The site should say two things at a glance: agriculture and livestock, and metrics (Scott, 2026-10-03;
he chose this layout, option C, from three mockups saved in `notes/`). So the headline sits on a photo
of cattle on open range, and three of this week's real numbers are pinned on the photo like survey
markers: the 550 lb steer price at the week's barn, this season's grass against normal (or the county's
fall field days in a week the Grazing Planner doesn't cover), and the county's trend corn yield. Each
pin links to its app or barn page. On tablets the pins sit in a row under the headline; on phones they stack.

- **The pins** are drawn by `hero.pins` from the same week `cards.py` saved, so they always match the
  panel below them (a test checks). Red means the downside and never comes alone: a down arrow and the
  words "below normal" go with it. A week with no fresh price says so in the pin.
- **The photo** is `static/photos/hero.jpg`, named in `config.py` (`HERO_PHOTO`) with its credit line
  (`HERO_CREDIT`), which is printed in the photo's corner. The build stops if a photo has no credit
  line, and with no photo file the band is plain deep green and the page still works. A dark wash over
  the left of the photo keeps the white headline readable whatever the picture.
- **Changing the photo:** Scott picks it (see Photos below) and saves the original in `notes/photos/`.
  Size a copy to about 2,000 px wide and under 400 KB, save it as `static/photos/hero.jpg`, update
  `HERO_CREDIT` if the source changed, then `python build.py`. The photo's address carries a short
  hash, so nobody keeps seeing the old one. The subject should sit right of center: the headline covers
  the left half on a computer.

## The live panel (under the photo)

Instead of a screenshot of an app, the home page shows the apps' real output for this week's county,
rebuilt every Friday: the 550 lb steer price and its range, how calves usually price this month
against the trend, the county's trend corn yield, and its fall field days (61 day squares), four tiles
in a row under the photo, then the "Tested before we trust it" numbers.
`hero.py` draws it from the same week `cards.py` saved. Each tile's gold callout says what stands
behind the number, so it must stay literally true: change the callout if the number's source changes.

### "See your county"

A **See your county** button in the panel lets a visitor pick their state and county; the steer
price, corn and field-day tiles switch to that county (the calves tile is the same everywhere). The
choice is kept in their own browser, so their next visit opens on their county, with **Change county**
and **County of the week** to switch back. Nothing is sent anywhere: no account, no location lookup.
The three pins on the photo switch with it (`herd_pin` per state and `pins` per county in
`panel-data.json`, format 2). Grass against normal is only known for the county of the week, so a
picked county's middle pin shows its fall field days.

- **How:** `build.py` writes `docs/panel-data.json`: every county's tiles, drawn in advance by the same
  `hero.py` functions as the page, so a picked county looks exactly like the county of the week.
  `static/panel.js` loads it only when someone uses the picker (or has used it before).
- **Which counties:** all 191 that either the Yield Predictor or the Equipment Planner covers
  (Nebraska and Iowa). A county only one app covers says so in the other tile.
- **The steer price by state:** the Friday job asks Herd Planner once per state (`herd_by_state` in
  `weeks.json`); the nearest barn with fresh sales differs by state. Iowa has no neighbor barns in
  Herd Planner yet, so Iowa shows Oklahoma City, and says so.
- **Search engines and first visits** always get the county of the week: the picker only changes what
  a returning visitor sees in their own browser.
- The file is about 470 KB but GitHub Pages sends it compressed (about 15 KB); a test keeps it under 700 KB.

### What the panel is called

A **KPI panel** (dashboard panel) of four **stat tiles**, each with a **microchart** and a
**callout**. The microcharts: a **bullet chart** (steer price and corn yield: a band for the range,
a dot for the value), a **sparkbar** (calves by month, a word-sized bar chart) and a **unit chart**
or **waffle chart** (the 61 day squares, one mark per day).

### What changes, and when

| Tile | Changes | Why |
| --- | --- | --- |
| Steer price | Weekly | Fresh price from Herd Planner each Friday, at the barn nearest the new county |
| Calves this month | Monthly | The highlighted month and its % move with the calendar |
| Corn yield | Weekly | A new county each week |
| Field days | Weekly | A new county each week |
| Heading ("This Week: ... County") | Weekly | Rotates through 88 counties |

Each app page's Recent Weeks table gains a row weekly. The "Why Use Our Apps" charts stay put until
a story is added or changed.

**What can stop it quietly:**

1. **No real prices online.** Herd Planner needs its automatic price updates running. With no price
   from the last three weeks, or no answer within about 4 minutes, the steer tile says "No fresh
   price" and the other three still update.
2. **GitHub pauses scheduled jobs after 60 days of no repository activity.** The job's own weekly
   commits should count, and GitHub emails before pausing. Look for a green check on Fridays.
3. **The county numbers themselves change once a year**, when you re-export them after new USDA
   yields. The weekly change comes from the rotating county.

**A quick Friday check:** open the site, or look for the commit "Weekly stat cards: 2026-W40"
(and so on) in the repository's history.

## Barn Prices: one page per sale barn

`barns.html` lists every sale barn Herd Planner follows, by state, with this week's 550 lb steer price;
each barn has its own page (`barn-kearney-ne-1848.html`: the town in the address because people search
by town, the USDA report number so two sales in one town never collide). A barn page shows:

- this week's 550 lb steer price and range, and the change from last week at the same barn (a red flag
  with a down arrow when it fell, blue when it rose),
- a price sheet: steers and heifers at 400 to 800 lb, $/cwt with ranges and $ a head,
- the last 12 weeks as a chart (a dot for the price, a bar for the range 8 in 10 sales fell in),
- **Best Months to Sell** (Herd Planner v0.21+, Milestone 16): for steer calves and heavy feeder steers, the
  typical year (a dot per month with its 95% range: the regional pattern for the months this barn sells, trend
  removed) and **this season** (one line: the last 12 months against this year's own trend line), with a
  plain sentence on the best and worst month and how this season compares. Months the barn never sells are
  greyed; a fall-only sale says it has no pattern of its own. `charts.best_months` draws it; the numbers come
  in `seasons` from `GET /suite/barns` and only the latest is kept in `barns.json`,
- the other barns in the same state, and how the numbers are worked out.

Every Friday `cards.py refresh` asks Herd Planner's public `GET /suite/barns` and adds the week to
`content/cards/barns.json` (two years kept per barn). A barn that hasn't sold in three weeks keeps its page
but says so instead of showing an old price. The live panel's steer tile links to the barn its price came
from. "Barn Prices" is in the site's menu, and every barn page is in `sitemap.xml`.

## The app tiles row

Under the live panel, one tile per app: every app in the suite list (`static/suite/suite-apps.json`),
then the apps being built (`"in_development"` in `content/apps.json`). The row scrolls sideways and snaps
to each tile: three show at a time on a wide screen with a peek of the next, arrow buttons appear when
there's more (`static/slider.js`), and phones swipe. It never moves by itself: auto-rotating carousels
are skipped by most visitors and hard to use.

When an app opens (the Grazing Planner, 2026-09-28): add it to `herd-planner/brand/suite-apps.json` and copy
that to every app and here, move its words from `"in_development"` to its own entry in `content/apps.json`,
copy its logo into `static/suite/suite-logos/`, give it a story (`content/stories.json`) and a section on
How We Test (`templates/methods.html`). The tests list anything missing. Apps without a card in the Friday
job (`build.WEEKLY`) get an app page with "This Season" instead of "This Week" and "Recent Weeks".

An app in development gets a dashed tile, an **In development** tag, its question, and **Get notified**,
which jumps to "Hear When Something New Opens" (Herd Planner's waitlist). It has no app page, no Farm Apps
menu entry and no footer link until it exists. Its logo goes in `static/soon/<id>.svg` (the suite's logo
style: a colored circle, a cream drawing, a gold accent). When it opens: add it to the master
`herd-planner/brand/suite-apps.json`, copy that out, write its entry in `apps.json`, and remove it from
`"in_development"` (a test fails if an app is in both).

**What each tile shows (chosen 2026-09-30, mockups in `notes/tile-mockups-2026-09-29.png`).** Top right, this
week's number from the app for the county of the week (`build.tile_stat`, from the same cards as the live
panel): Herd Planner the 550 lb steer price and its barn, the Yield Predictor the county's trend corn yield,
the Grazing Planner this season's grass against normal (red with a down arrow only when it's below), the
Equipment Planner fall field days. A week without a number (a stale steer price, an Iowa county for the
Grazing Planner) leaves the corner empty. Bottom right, "Free to try"; "Plan from $X/mo" joins it once
`SHOW_PRICES = True` in `config.py` (after billing exists), using `"price_from"` in `content/apps.json`.

## Each app on a computer and a phone (Our Farm Apps)

Each app's row shows the app on a computer, its own header joined straight to a real answer, with the same
answer on a phone in front (chosen 2026-09-30; mockups in `notes/shot-mockups-*.png`). The pictures are
`static/shots/<app id>-computer.jpg` (1100 px wide) and `-phone.jpg` (360 px wide); `"shot_alt"` in
`content/apps.json` describes them for screen readers. An app without both pictures keeps the plain
placeholder. The first set (2026-09-30) was taken from each app running with real data: Herd Planner's demo
ranch (keep or sell a steer calf), the Grazing Planner's Aug 1 check (Frontier County, 2,000 acres, 120
pairs), the Yield Predictor's map and Hall County, the Equipment Planner's buy, lease or hire for Hall
County. Retake them when an app's look changes: desktop at 1000 x 750, phone at 390 wide, both at 2x,
then shrink to those widths as JPEG (quality about 84). A test keeps the set under 900 KB.

## The app pages: This Week and What the Numbers Show (2026-09-30)

- **Herd Planner's This Week** (`build.herd_week_card`, option C of three mockups in `notes/hp-week-A/B/C.png`):
  the 550 lb steer price at the week's barn with its 8-in-10 band (`hero.range_bar`), about what a head brings,
  then **Sell now or wait?**: that barn's steer-calf months against an average month (`hero.month_strip`, this
  month dark), in words: now, the best month and the worst ("Now (September): about 3% below an average month.
  March typically runs about 5% above..."), from the barn's own `seasons` in `content/cards/barns.json`. It links to
  the barn's page. With no fresh price or no season pattern, the plain stat card shows instead.
  **A slider** (Scott, same day): the card above is slide 1, and slide 2 is **the barn's whole price sheet** (steers and
  heifers, 400 to 800 lb: a dot at the price and a pale 8-in-10 band, on a shared $ scale rather than bars from a
  cut-off axis; "Show the numbers" has the table). Swipe, or the arrows under the card, with dots for which card is
  showing (`slider.js`, shared with the home page's tiles; `data-dots`). A photo card can join as a slide once there
  are licensed photos.
- **What the Numbers Show** on every app page: a one-line intro, the charts in a compact grid (two side by side
  when an app has two, one at most 640 px wide otherwise, stacked on phones), and a **How to read it** line on each
  chart (`how_to_read` in `content/stories.json`; a test requires one for every story). Scott: the charts were
  "way too big" and unexplained. The home page's Why Use Our Apps is unchanged.
- **Photos** (Scott wants ranch and sale-barn pictures): only licensed ones (Unsplash or Pexels licenses, public
  domain USDA/NRCS, paid stock, or your own or a ranch's with written OK); Scott picks and downloads them into
  `notes/photos/` with where each came from, then they're sized and built in. USDA ARS photos ask for the
  credit "Photo courtesy of USDA ARS" (or with the photographer's name), and nothing on the page may suggest
  USDA endorses the apps. The first one in use is the home page's photo (see "The top of the home page").

## Why Use Our Apps

A home page section (and a "What the Numbers Show" section on each app page) with one real finding
per chart: when calves sell best, how many heifers to keep, what explains a county's corn yield,
and when owning a combine beats hiring. Each lives in `content/stories.json` with its numbers,
words, limits and source; `charts.py` draws it as an SVG that `build.py` writes into the page.

- **Every number comes from the app's own notebook or README**, named in `source`. A test fails
  if a story has no source, no caution, or belongs to an app that isn't in the suite list.
- **Add a story:** add an entry to `stories.json`. A new chart shape needs a new function in
  `charts.py` and a line in its `KINDS` table.
- Hovering a bar or point shows its value; **Show the numbers** opens the same numbers as a table.

## The weekly stat cards

A GitHub Action (`.github/workflows/weekly-cards.yml`) runs every Friday morning: tests, then
`python cards.py refresh` (picks the county, asks Herd Planner's public `/suite/summary` for the steer
price, waiting up to about 4 minutes for it to wake), then `python build.py`, then commits and pushes.
Run it by hand from GitHub: **Actions > Weekly stat cards > Run workflow**. Because it pushes to
GitHub, start every work session with `git pull` (see **Git in this project** below).

- **The county of the week** rotates through the 88 counties both county apps cover, in a fixed
  shuffled order, so each comes around about every 21 months.
- **No price that week** (Herd Planner asleep too long, or only sample prices): the card says so; the
  corn and field-day cards still show. Sample prices are never published.
- **New yields or weather:** export the cards in those projects (`python scripts\export_suite_card.py`
  in crop-yield-predictor, `python -m calculators.suite_card` in farm-equipment-planner), then here
  `python cards.py refresh` copies the new files into `content/cards/`. Commit and push them.
- **The Grazing Planner's grass** (for the app tile): `refresh` asks its public `/api/season` and
  `/api/plan` for the county (Nebraska only), the same answer anyone gets on its page. It sleeps on
  Render's free plan too, so it gets the same wait. An Iowa county has no grass card that week.
- A number shown for a week is saved in `content/cards/weeks.json` and never changes afterwards.

Search engines only see this once `PUBLIC = True` in `config.py` (it switches off `noindex` and points
`robots.txt` at `sitemap.xml`). Set `SITE_URL` to the company domain when the site moves.

## Git in this project

This repository has two authors: you, and the weekly job, which commits the new week to GitHub
every Friday. So the copy on your computer falls behind GitHub every week, even when you haven't
touched anything. Git never updates your copy on its own; you ask it to with `git pull`.

**Start of every session, before you edit anything:**

```powershell
git pull
```

`git pull` does two things in one: it downloads the commits that are on GitHub but not on your
computer (that part alone is `git fetch`), then merges them into your files. With no edits of your
own, it simply fast-forwards your copy to match GitHub. You'll see the files it changed, usually
`content/cards/weeks.json` and a few pages in `docs/`, or "Already up to date."

**End of a session:**

```powershell
git status
```

```powershell
git add -A
```

```powershell
git commit -m "What you changed, in a few words"
```

```powershell
git push
```

| Command | What it does |
| --- | --- |
| `git status` | Lists files you changed, files not yet added, and whether you're ahead of or behind GitHub. Changes nothing. Safe any time. |
| `git pull` | `git fetch` + merge: brings GitHub's new commits into your folder. |
| `git fetch` | Downloads GitHub's new commits without touching your files; `git status` then says how far behind you are. |
| `git add -A` | Marks every change (new, edited, deleted files) to go into the next commit. |
| `git commit -m "..."` | Saves the marked changes as one snapshot on your computer only. |
| `git push` | Sends your commits to GitHub. The site republishes a minute later. |
| `git log --oneline -10` | The last 10 commits, one line each; the weekly ones say "Weekly stat cards: 2026-W40". |
| `git diff` | Shows exactly which lines you changed and haven't committed yet. |

**If `git push` says "rejected ... (fetch first)"**: GitHub has commits you don't (usually a Friday
update). Nothing is lost. Run `git pull`, then `git push` again.

**If `git pull` says "Need to specify how to reconcile divergent branches"**: newer Git wants you to
choose once how pulls combine your commits with GitHub's. Merging is the simplest:

```powershell
git config --global pull.rebase false
```

Then `git pull` again. If an editor opens asking for a merge message, the one it suggests is fine:
save and close it.

**If `git pull` reports a CONFLICT**: you and the weekly job changed the same lines. Almost always
that's in `docs/` or `content/cards/weeks.json`, which are made by scripts, never by hand. Keep
GitHub's weeks file and rebuild the pages:

```powershell
git checkout --theirs content/cards/weeks.json
```

```powershell
python build.py
```

```powershell
git add -A
```

```powershell
git commit -m "Merge the weekly update"
```

(`--theirs` means "the version coming from GitHub" during a pull.) A conflict in a file you did edit
by hand, like a template, shows both versions between `<<<<<<<` and `>>>>>>>` markers: keep the lines
you want, delete the markers, then `git add -A` and `git commit`.

To avoid most of this, pull at the start and push at the end of each session, and try not to leave
edits uncommitted over a Friday morning.

## Put it online (free)

1. Create a GitHub repository for it and push this folder.
2. On GitHub: **Settings > Pages > Build and deployment**, Source **Deploy from a branch**,
   branch **master**, folder **/docs**, then **Save**.
3. After a minute the site is at `https://<your-username>.github.io/<repository-name>/`.

When there's a domain, the same Pages settings page has a **Custom domain** box.
