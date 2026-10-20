// Signed in, the header says so (2026-10-20). Scott: "no matter which app I sign in to, when I go to the company home
// page it says Sign In as if I am not already. Maybe it should say Sign Out if I'm logged in?" He chose B of
// notes/site-signout-sheet-*-2026-10-20.png: a menu under your first name with My Farm and Sign Out, as in the apps.
// This site (cornerpostlogic.com) and My Farm (apps.cornerpostlogic.com) are the same site to a browser, so asking My
// Farm with credentials sends its own sign-in cookie along; this site sets no cookie and reads none. My Farm answers
// only this site's addresses, and only yes or no plus, on a yes, the first name for the menu (never the email).
// Every app signs in through My Farm, so its answer speaks for all of them. The page starts as a visitor sees it
// (Sign In); only a yes swaps in the menu, so no JavaScript, My Farm asleep or no answer leaves Sign In, which is
// never wrong, only late.
"use strict";
(function () {
  var me = document.currentScript;
  var origin = me && me.getAttribute("data-account");
  if (!origin || typeof fetch !== "function") return;
  var all = function (sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); };

  function draw(signedIn, label) {
    all("a.nav-signin").forEach(function (a) { a.hidden = signedIn; });
    all("details.nav-me").forEach(function (menu) { menu.hidden = !signedIn; if (!signedIn) menu.open = false; });
    if (signedIn && label) all(".nav-me-name").forEach(function (span) { span.textContent = label; });
  }

  function ask() {
    var stop = typeof AbortController === "function" ? new AbortController() : null;
    var timer = stop ? setTimeout(function () { stop.abort(); }, 20000) : null;   // My Farm may be waking up
    fetch(origin + "/site/status", { credentials: "include", cache: "no-store", signal: stop ? stop.signal : undefined })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (answer) {
        var yes = !!(answer && answer.signed_in === true);
        draw(yes, yes && typeof answer.label === "string" ? answer.label.slice(0, 24) : "");
      })
      .catch(function () { /* no answer: Sign In stays */ })
      .then(function () { if (timer) clearTimeout(timer); });
  }

  document.addEventListener("click", function (ev) {
    var button = ev.target && ev.target.closest ? ev.target.closest(".nav-signout") : null;
    if (!button) return;
    ev.preventDefault();
    all(".nav-signout").forEach(function (b) { b.disabled = true; });
    fetch(origin + "/site/sign-out", { method: "POST", credentials: "include", cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error(String(r.status));
        draw(false);
        var signIn = all("a.nav-signin").filter(function (a) { return a.getClientRects().length; })[0];
        if (signIn) signIn.focus();   // the button the keyboard was on has gone: hand it to Sign In
      })
      .catch(function () {
        all(".nav-signout").forEach(function (b) { b.textContent = "Sign Out: Try Again"; });
      })
      .then(function () { all(".nav-signout").forEach(function (b) { b.disabled = false; }); });
  });

  // The name menu acts like the site's other menu: one open at a time, and a click elsewhere or Escape closes it.
  document.addEventListener("toggle", function (ev) {
    var opened = ev.target;
    if (!opened || !opened.open || !opened.matches || !opened.matches("details.nav-me, details.mega")) return;
    all("details.nav-me, details.mega").forEach(function (other) { if (other !== opened) other.open = false; });
  }, true);
  document.addEventListener("click", function (ev) {
    all("details.nav-me[open]").forEach(function (menu) { if (!menu.contains(ev.target)) menu.open = false; });
  });
  document.addEventListener("keydown", function (ev) {
    if (ev.key !== "Escape") return;
    all("details.nav-me[open]").forEach(function (menu) { menu.open = false; menu.querySelector("summary").focus(); });
  });

  ask();
  // Brought back with the Back button: the sign-in may have changed in another tab or app since.
  window.addEventListener("pageshow", function (ev) { if (ev.persisted) ask(); });
})();
