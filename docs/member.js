// Which of our apps this browser has used, so the menu can offer "Open Herd Planner" in place of "Sign In"
// (Scott, 2026-10-05: "the link up top says Sign In as if I am not already logged in even when I am").
// This site is on its own domain, so it can never see an app's sign-in. Instead, the app's link back here ends
// in #uses=<app id> while a person is signed in there (and #left=<app id> after they sign out), and this page
// keeps that one word in the browser (localStorage "cpl.uses"): which app, never who. It is a memory, not a
// check: the sign-in may have run out since, which is why the link says "Open", and Open is true either way.
// It runs in the page's head, before anything is drawn, and sets data-uses on <html>; the two style rules per
// app in the head (build.member_css) then hide that app's sign-up links and show its Open link. No storage, no
// JavaScript, or an app we don't know: the page stays as a new visitor sees it.
"use strict";
(function () {
  var KEY = "cpl.uses";
  var me = document.currentScript;
  var apps = ((me && me.getAttribute("data-apps")) || "").split(" ").filter(Boolean);
  var root = document.documentElement;
  var read = function () { try { return localStorage.getItem(KEY); } catch (e) { return null; } };
  var write = function (id) { try { id ? localStorage.setItem(KEY, id) : localStorage.removeItem(KEY); } catch (e) { /* fine */ } };
  var show = function () {
    var id = read();
    if (id && apps.indexOf(id) > -1) root.setAttribute("data-uses", id); else root.removeAttribute("data-uses");
  };
  var arrive = function () {
    var mark = /^#(uses|left)=([a-z0-9-]{1,40})$/.exec(location.hash);
    if (mark && apps.indexOf(mark[2]) > -1) {
      if (mark[1] === "uses") write(mark[2]); else if (read() === mark[2]) write(null);
      // The mark has done its job: take it out of the address so it isn't bookmarked or shared.
      try { history.replaceState(null, "", location.pathname + location.search); } catch (e) { /* fine */ }
    }
    show();
  };
  arrive();
  window.addEventListener("hashchange", arrive);   // the same tab, already on this site, sent here again
  // A tab that was already open, or one brought back with the Back button, catches up with the others.
  window.addEventListener("storage", function (ev) { if (ev.key === KEY || ev.key === null) show(); });
  window.addEventListener("pageshow", show);
  // "Forget this": back to what a new visitor sees.
  document.addEventListener("click", function (ev) {
    var button = ev.target && ev.target.closest ? ev.target.closest("[data-forget-app]") : null;
    if (!button) return;
    ev.preventDefault();
    write(null);
    show();
    if (button.getAttribute("data-done")) { button.textContent = button.getAttribute("data-done"); button.disabled = true; }
    // The button's own line may have just gone with the rest: hand the keyboard to the first sign-up link
    // rather than leave it nowhere.
    if (!button.getClientRects().length) {
      var next = document.querySelector("main a.visitor-only") || document.querySelector(".site-nav .nav-visitor");
      if (next) next.focus();
    }
  });
})();
