"""The header's hover line (2026-10-18; Scott, on the home page: "the yellow lines do not appear under the menu options
with mouse overs"). On a computer the header links and Our Farm Apps show the page-you're-on gold line while pointed at
(or open), as the apps' headers do; Sign In and Sign Up keep their own button hover."""

import build


def test_the_header_links_get_the_gold_line_on_hover():
    css = (build.STATIC / "site.css").read_text(encoding="utf-8")
    current = '.site-nav > a[aria-current="page"] { color: #fff; box-shadow: 0 2px 0 var(--suite-gold); }'
    assert current in css
    at = css.index("@media (min-width: 641px) {\n  .site-nav > a:not(.nav-signin):not(.nav-signup):hover")
    rule = css[at:css.index("}\n}", at)]
    for sel in (".site-nav > a:not(.nav-signin):not(.nav-signup):hover", ".mega > summary:hover", ".mega[open] > summary"):
        assert sel in rule, sel
    assert "box-shadow: 0 2px 0 var(--suite-gold);" in rule      # the same straight line as the current page
