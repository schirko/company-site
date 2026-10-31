"""Contact Us (2026-10-30; Scott: "I like B", notes/site-contact-B-*-2026-10-30.png): a form sent through Web3Forms,
beside the other ways to reach us. The access key comes from the CORNERPOST_WEB3FORMS_KEY setting or web3forms_key.txt
(Git-ignored), never from a file in Git."""
from pathlib import Path

import pytest

import build
import config

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def site():
    return build.build()


def text(p):
    return p.read_text(encoding="utf-8")


def test_the_page_is_built_and_every_footer_links_to_it(site):
    page = text(site / "contact.html")
    assert "<h1>Contact Us</h1>" in page and "Other Ways to Reach Us" in page and 'src="contact.js' in page
    assert ('id="contact-form"' in page) != ('class="cf-off"' in page)          # the form, or the email line, never both
    for name in ("index.html", "about.html", "privacy.html", "contact.html"):
        assert '<a href="contact.html">Contact</a>' in text(site / name), name
    assert 'href="contact.html">contact form</a>' in text(site / "about.html")
    assert "contact.html" in text(site / "sitemap.xml")


def test_with_a_key_the_form_sends_to_web3forms():
    form = build.contact_form("not-a-real-key")
    assert 'action="https://api.web3forms.com/submit" method="POST"' in form
    assert 'name="access_key" value="not-a-real-key"' in form and 'name="botcheck" class="cf-trap"' in form
    for field in ('name="name"', 'name="email"', 'name="about"', 'name="message"'):
        assert field in form
    assert all(f"<option>{build.e(t)}</option>" in form for t in build.CONTACT_TOPICS)
    assert 'href="privacy.html#contact-form"' in form and "deletes its copy after 30 days" in form


def test_without_a_key_it_says_to_email_instead():
    off = build.contact_form("")
    assert "contact-form" not in off and f'mailto:{config.EMAIL}' in off


def test_the_key_is_never_in_a_file_git_keeps(monkeypatch, tmp_path):
    assert "web3forms_key.txt" in text(ROOT / ".gitignore")
    monkeypatch.setenv("CORNERPOST_WEB3FORMS_KEY", "from-the-setting")
    assert config.web3forms_key() == "from-the-setting"
    for p in (ROOT / "config.py", ROOT / "build.py"):
        assert "access_key\" value=\"" not in text(p).replace('value="{e(key)}"', "")


def test_the_script_says_how_it_went_and_builds_no_markup():
    js = text(ROOT / "static/contact.js")
    assert "innerHTML" not in js and "textContent" in js
    assert "if (data.botcheck) return;" in js and "Thanks, your message is on its way." in js


def test_privacy_says_where_a_message_goes(site):
    page = text(site / "privacy.html")
    assert 'id="contact-form"' in page and "Web3Forms" in page and "30 days" in page
