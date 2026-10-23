"""Check every link in the suite: the company site and every app (Scott, 2026-10-22: "I also want to make sure none are
broken"). Opens each page in a real browser (Chromium through Playwright, so links the page's JavaScript draws count
too), follows every link, and reports the ones that don't work.

    python tools/check_links.py                     the live sites (the weekly GitHub job runs this)
    python tools/check_links.py --map hosts.json    copies running on your own computer: each live address is sent
                                                    to the local copy named in the file, e.g.
                                                    {"https://cornerpostlogic.com": "http://127.0.0.1:8092"}

What counts as broken:
- a link to one of our own pages (the site or an app) that doesn't open (an error, 404, 500, a timeout)
- a jump link (#part) whose part isn't on the page it points to
- live only: a link to another site that answers with an error. Some sites refuse robots (403, 429): those are listed
  as "check by hand", not broken.

Also listed: every outside site linked, with how many links, and any link to an address of ours this file doesn't
know (a typo in a domain shows up there). Nothing is signed into unless --login says so, and nothing that changes
anything is followed (sign-out, delete, remove, the Django admin).

Needs: pip install playwright, then python -m playwright install chromium (the weekly job does both).
Exit status 1 when anything is broken, so a job fails and says so.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from urllib.parse import urldefrag, urljoin, urlsplit

# Our own addresses: every page under these is crawled and must work.
OURS = ["https://cornerpostlogic.com", "https://www.cornerpostlogic.com", "https://apps.cornerpostlogic.com",
        "https://herd-planner.onrender.com", "https://grazing-planner.onrender.com",
        "https://farm-equipment-planner.onrender.com", "https://farm-account.onrender.com",
        "https://nebraska-yield-predictor-izzr8x4rxcppkcfjmqmiej.streamlit.app",
        "https://yield-predictor.onrender.com"]      # the Yield Predictor's web app (its v0.2.0, beside the Streamlit one)
START = ["https://cornerpostlogic.com/", "https://herd-planner.onrender.com/", "https://grazing-planner.onrender.com/app/",
         "https://farm-equipment-planner.onrender.com/", "https://apps.cornerpostlogic.com/app/",
         "https://yield-predictor.onrender.com/"]
# Streamlit draws everything with JavaScript inside its own frame and has no links of ours to follow: the address is
# checked, not crawled.
NOT_CRAWLED = ("https://nebraska-yield-predictor-izzr8x4rxcppkcfjmqmiej.streamlit.app",)
# Never followed: they change something, or are someone else's admin.
SKIP = re.compile(r"(sign-?out|log-?out|/delete|/remove|/admin/|/close\b|/unsubscribe|calendar\.ics$)", re.I)
# Pages that are only for files: checked (they must answer) but not opened as pages.
FILE = re.compile(r"\.(xlsx|csv|pdf|png|jpe?g|svg|ics|json|zip|txt)(\?|$)", re.I)
# My Farm is one page whose #account, #barns, #follow/1280 ... are its own pages (the script reads the address), not
# parts of the page: there a #mark is a route, not an id to look for.
# Marks an app reads to open the right card or step (Herd Planner's #waitlist, #signup, #signin from the company site,
# #go/<step> from My Farm's wheel, #reset/<code> from an email): not ids, so not looked for.
APP_MARKS = re.compile(r"^(waitlist|signup|signin|join|go/.+|reset/.+|help/.+|card/.+)$")
HASH_ROUTED = ("https://apps.cornerpostlogic.com", "https://farm-account.onrender.com")
ROBOT_SHY = {401, 403, 405, 429, 999}      # outside sites that refuse robots; checked by hand
MAX_PAGES = 400                            # per address of ours, a guard against a link that makes endless pages
WAIT_MS = 600                              # after the page settles, for links drawn a moment later


@dataclass
class Report:
    pages: int = 0
    checked: dict = field(default_factory=dict)             # url -> status (int) or error text
    broken: list = field(default_factory=list)              # (on page, link, why)
    by_hand: list = field(default_factory=list)
    outside: dict = field(default_factory=lambda: defaultdict(int))
    unknown_ours: list = field(default_factory=list)
    signed_in_only: list = field(default_factory=list)      # (on page, link): 401/403 while signed out
    not_here: set = field(default_factory=set)              # ours, but no local copy to check it against


def origin(url: str) -> str:
    s = urlsplit(url)
    return f"{s.scheme}://{s.netloc}"


class Checker:
    def __init__(self, browser, host_map: dict[str, str], live: bool, logins: list):
        self.map = {k.rstrip("/"): v.rstrip("/") for k, v in host_map.items()}
        self.back = {v: k for k, v in self.map.items()}
        self.live = live
        self.ctx = browser.new_context(viewport={"width": 1280, "height": 900}, ignore_https_errors=not live)
        self.page = self.ctx.new_page()
        self.report = Report()
        self.seen_pages: set[str] = set()
        self.per_origin = defaultdict(int)
        self.ids: dict[str, set[str]] = {}
        self.want_ids: list[tuple[str, str, str]] = []      # (on page, target page, id)
        for path, body in logins:                            # e.g. a local test account
            r = self.ctx.request.post(self.local(path), data=json.loads(body),
                                      headers={"Content-Type": "application/json"})
            print(f"sign-in {path}: {r.status}")

    def local(self, url: str) -> str:
        """Where to actually ask for a live address (the same address when checking the live sites)."""
        o = origin(url)
        return self.map[o] + url[len(o):] if o in self.map else url

    def live_name(self, url: str) -> str:
        o = origin(url)
        return self.back[o] + url[len(o):] if o in self.back else url

    def ours(self, url: str) -> bool:
        return origin(url) in OURS

    def fetch(self, url: str):
        if url in self.report.checked:
            return self.report.checked[url]
        try:
            r = self.ctx.request.get(self.local(url), timeout=90_000, max_redirects=10)
            status = r.status
            if status in (405, 501):
                status = self.ctx.request.head(self.local(url), timeout=90_000).status
        except Exception as err:                              # noqa: BLE001 - every failure is a broken link
            status = f"no answer ({str(err).splitlines()[0][:80]})"
        self.report.checked[url] = status
        return status

    def visit(self, url: str) -> list[tuple[str, str]]:
        """Open one of our pages and return its links (href, its text) as the browser sees them."""
        self.page.goto(self.local(url), wait_until="networkidle", timeout=90_000)
        self.page.wait_for_timeout(WAIT_MS)
        self.ids[url] = set(self.page.eval_on_selector_all("[id]", "els => els.map(e => e.id)"))
        self.ids[url] |= set(self.page.eval_on_selector_all("a[name]", "els => els.map(e => e.name)"))
        links = self.page.eval_on_selector_all(
            "a[href]", "els => els.map(e => [e.getAttribute('href'), (e.textContent || '').trim().slice(0, 60),"
                       " e.getAttribute('role') || '', e.hasAttribute('download')])")
        here = self.live_name(self.page.url)
        return [(urljoin(here, h), t, role, dl) for h, t, role, dl in links]

    def run(self, start: list[str]) -> Report:
        queue = deque(start)
        while queue:
            url = queue.popleft()
            key = urldefrag(url)[0]
            if key in self.seen_pages:
                continue
            self.seen_pages.add(key)
            o = origin(key)
            self.per_origin[o] += 1
            if self.per_origin[o] > MAX_PAGES:
                continue
            status = self.fetch(key)
            if not (isinstance(status, int) and status < 400):
                continue                                      # reported where it was linked from
            try:
                links = self.visit(key)
            except Exception as err:                          # noqa: BLE001
                self.report.broken.append((key, key, f"page didn't open: {str(err).splitlines()[0][:90]}"))
                continue
            self.report.pages += 1
            print(f"[{self.report.pages}] {key}  ({len(links)} links)")
            for href, text, role, download in links:
                self.check(key, href, text, role, download, queue)
        for on, target, frag in self.want_ids:
            if target in self.ids and frag not in self.ids[target] and not APP_MARKS.match(frag):
                self.report.broken.append((on, f"{target}#{frag}", "the part it jumps to isn't on that page"))
        return self.report

    def check(self, on: str, href: str, text: str, role: str, download: bool, queue: deque) -> None:
        scheme = urlsplit(href).scheme
        if scheme in ("javascript", "mailto", "tel", "data", "blob"):
            return
        target, frag = urldefrag(href)
        if frag and origin(target) in HASH_ROUTED:            # My Farm's own pages: the address is checked below
            frag = ""
        if frag and target == on:                             # a jump within the page
            if frag not in self.ids.get(on, set()) and not APP_MARKS.match(frag):
                self.report.broken.append((on, href, f'"{text}" jumps to #{frag}, which isn\'t on the page'))
            return
        if not frag and target == on and role == "button":    # href="#" buttons drawn by the page's script
            return
        if SKIP.search(target):
            return
        if not self.ours(target):
            if origin(target).endswith((".cornerpostlogic.com", "cornerpostlogic.com", ".onrender.com")):
                self.report.unknown_ours.append((on, href))
            self.report.outside[origin(target)] += 1
            if self.live:
                status = self.fetch(target)
                if isinstance(status, int) and status in ROBOT_SHY:
                    self.report.by_hand.append((on, href, status))
                elif not (isinstance(status, int) and status < 400):
                    self.report.broken.append((on, href, f'"{text}": {status}'))
            return
        if not self.live and origin(target) not in self.map:
            self.report.not_here.add(origin(target))          # e.g. the Yield Predictor: no local copy
            return
        status = self.fetch(target)
        if status in (401, 403):
            self.report.signed_in_only.append((on, href))     # works once signed in; --login checks those
            return
        if not (isinstance(status, int) and status < 400):
            self.report.broken.append((on, href, f'"{text}": {status}'))
            return
        if frag:
            self.want_ids.append((on, target, frag))
        if not download and not FILE.search(target) and not target.startswith(NOT_CRAWLED):
            queue.append(target)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--map", help="JSON file: live address -> local copy")
    parser.add_argument("--start", nargs="*", help="pages to start from (live addresses; default: every site's front)")
    parser.add_argument("--login", nargs=2, action="append", default=[], metavar=("PATH", "JSON"),
                        help="sign in first: POST this JSON to this address (a local test account only)")
    parser.add_argument("--out", help="also write the report here as JSON")
    args = parser.parse_args()
    host_map = json.load(open(args.map, encoding="utf-8")) if args.map else {}
    from playwright.sync_api import sync_playwright

    t0 = time.time()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        checker = Checker(browser, host_map, live=not host_map, logins=args.login)
        rep = checker.run(args.start or START)
        browser.close()
    print(f"\n{rep.pages} pages opened, {len(rep.checked)} addresses checked in {time.time() - t0:.0f} s")
    groups = defaultdict(list)
    for on, link, why in rep.broken:
        groups[(link, why)].append(on)
    print(f"\nBroken: {len(groups)} links ({len(rep.broken)} places)")
    for (link, why), ons in sorted(groups.items()):
        more = f" and {len(ons) - 1} more page{'s' if len(ons) > 2 else ''}" if len(ons) > 1 else ""
        print(f"  {link}\n    {why}\n    on {ons[0]}{more}")
    if rep.signed_in_only:
        need = sorted({link for _, link in rep.signed_in_only})
        print(f"\nNeed a sign-in (answered 401/403 signed out; not broken): {len(need)}")
        for link in need:
            print(f"  {link}")
    if rep.not_here:
        print("\nOurs, but no local copy to check against (checked in the live run): " + ", ".join(sorted(rep.not_here)))
    if rep.by_hand:
        print(f"\nCheck by hand (the site refuses robots): {len(rep.by_hand)}")
        for on, link, status in rep.by_hand:
            print(f"  {link} ({status}) on {on}")
    if rep.unknown_ours:
        print(f"\nLinks to an address of ours this checker doesn't know (a typo?): {len(rep.unknown_ours)}")
        for on, link in rep.unknown_ours:
            print(f"  {link} on {on}")
    print("\nOutside sites linked:" + ("" if rep.outside else " none"))
    for o, n in sorted(rep.outside.items(), key=lambda kv: -kv[1]):
        print(f"  {n:4d}  {o}")
    if args.out:
        json.dump({"pages": rep.pages, "broken": rep.broken, "signed_in_only": rep.signed_in_only, "by_hand": rep.by_hand, "outside": rep.outside,
                   "unknown_ours": rep.unknown_ours}, open(args.out, "w", encoding="utf-8"), indent=1)
    return 1 if rep.broken else 0


if __name__ == "__main__":
    sys.exit(main())
