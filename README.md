# Company website

The front door for the farm apps: Herd Planner, the Yield Predictor and the
Farm Equipment Planner. A few plain pages (home, About, How we test, Privacy), built by a small Python script and served
free by GitHub Pages.

The company name isn't chosen yet, so the site says **Placeholder Ag** and asks search
engines not to list it. When the name is settled, change it in `config.py`, set
`PUBLIC = True`, rebuild, and push.

## How it's put together

```
FirstLightAg/
├── config.py          the company name, tagline, location, contact address, PUBLIC switch
├── build.py           fills in the templates and writes the finished site to docs/
├── templates/         the pages, with ${placeholders} for the name and the app list
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
cd B:\_Dev\Python\FirstLightAg
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python build.py
pytest
python -m http.server 8080 --directory docs
```

Then open http://127.0.0.1:8080 in a browser.

## Put it online (free)

1. Create a GitHub repository for it and push this folder.
2. On GitHub: **Settings > Pages > Build and deployment**, Source **Deploy from a branch**,
   branch **main**, folder **/docs**, then **Save**.
3. After a minute the site is at `https://<your-username>.github.io/<repository-name>/`.

When there's a domain, the same Pages settings page has a **Custom domain** box.
