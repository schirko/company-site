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
├── charts.py          draws the "Why Use Our Apps" charts as SVG, in plain Python
├── hero.py            the home page's live panel: this week's numbers as a small dashboard
├── templates/         the pages, with ${placeholders} for the name and the app list
├── content/apps.json  the home page's longer words about each app (tiles and app sections)
├── content/stories.json  the "Why Use Our Apps" findings: numbers, words and sources
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

## The live panel (top of the home page)

Instead of a screenshot of an app, the top of the home page shows the apps' real output for this
week's county, rebuilt every Friday: the 550 lb steer price and its range, how calves usually price
this month against the trend, the county's trend corn yield, and its fall field days (61 day squares).
`hero.py` draws it from the same week `cards.py` saved. Each tile's gold callout says what stands
behind the number, so it must stay literally true: change the callout if the number's source changes.

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
