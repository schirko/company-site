// Signed in, the header says so (2026-10-20). Scott: "no matter which app I sign in to, when I go to the company home
// page it says Sign In as if I am not already. Maybe it should say Sign Out if I'm logged in?" He chose A of
// notes/site-signout-sheet-*-2026-10-20.png: My Farm and Sign Out.
// This site (cornerpostlogic.com) and My Farm (apps.cornerpostlogic.com) are the same site to a browser, so asking My
// Farm with credentials sends its own sign-in cookie along; this site sets no cookie and reads none. My Farm answers
// only yes or no (no name, no email) and only to this site's addresses. Every app signs in through My Farm, so its
// answer speaks for all of them. The page starts as a visitor sees it (Sign In); only a yes swaps in My Farm and
// Sign Out, so no JavaScript, My Farm asleep or no answer leaves Sign In, which is never wrong, only late.
"use strict";
(function () {
  var me = document.currentScript;
  var origin = me && me.getAttribute("data-account");
  if (!origin || typeof fetch !== "function") return;
  var all = function (sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); };

  function draw(signedIn) {
    all("a.nav-signin").forEach(function (a) { a.hidden = signedIn; });
    all(".nav-farm, .nav-signout").forEach(function (el) { el.hidden = !signedIn; });
  }

  function ask() {
    var stop = typeof AbortController === "function" ? new AbortController() : null;
    var timer = stop ? setTimeout(function () { stop.abort(); }, 20000) : null;   // My Farm may be waking up
    fetch(origin + "/site/status", { credentials: "include", cache: "no-store", signal: stop ? stop.signal : undefined })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (answer) { draw(!!(answer && answer.signed_in === true)); })
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

  ask();
  // Brought back with the Back button: the sign-in may have changed in another tab or app since.
  window.addEventListener("pageshow", function (ev) { if (ev.persisted) ask(); });
})();
