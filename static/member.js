// Which of our apps this browser has used, so the menu can offer "Open Herd Planner" in place of "Sign In"
// (Scott, 2026-10-05: "the link up top says Sign In as if I am not already logged in even when I am").
// This site is on its own domain, so it can never see an app's sign-in. Instead, the app's link back here ends
// in #uses=<app id> while a person is signed in there (and #left=<app id> after they sign out), and this page
// keeps that one word in the browser (localStorage "cpl.uses"): which app, never who. It is a memory, not a
// check: the sign-in may have run out since, which is why the link says "Open", and Open is true either way.
// It runs in the page's head, before anything is drawn, and sets data-uses on <html>; the two style rules per
// app in the head (build.member_css) then hide that app's sign-up links and show its Open link. No storage, no
// JavaScript, or an app we don't know: the page stays as a new visitor sees it.
//
// 2026-10-20, the Our Farm Apps menu (Scott: "a sign in check needs to be done and then send the user to the actual
// app if signed in, or the splash page ... if not"). Each app's row in the menu opens its page here. In a browser
// whose last trip back from an app said #uses=<that app>, the row opens the app's own /open instead (data-open):
// the app checks its sign-in and sends a signed-in person in, anyone else back to that page here. The apps this
// browser has used are kept as a list of ids (localStorage "cpl.open"), which apps, never who; #left takes one off.
// A new visitor's menu never touches an app, so nobody waits for a sleeping server just to land back here.
"use strict";
(function () {
  var KEY = "cpl.uses", OPEN = "cpl.open";
  var me = document.currentScript;
  var apps = ((me && me.getAttribute("data-apps")) || "").split(" ").filter(Boolean);
  var menuApps = ((me && me.getAttribute("data-open-apps")) || "").split(" ").filter(Boolean);
  var root = document.documentElement;
  var read = function () { try { return localStorage.getItem(KEY); } catch (e) { return null; } };
  var write = function (id) { try { id ? localStorage.setItem(KEY, id) : localStorage.removeItem(KEY); } catch (e) { /* fine */ } };
  var opened = function () {
    var list;
    try { list = (localStorage.getItem(OPEN) || "").split(" "); } catch (e) { list = []; }
    return list.filter(function (id) { return menuApps.indexOf(id) > -1; });
  };
  var keep = function (list) { try { list.length ? localStorage.setItem(OPEN, list.join(" ")) : localStorage.removeItem(OPEN); } catch (e) { /* fine */ } };
  var show = function () {
    var id = read();
    if (id && apps.indexOf(id) > -1) root.setAttribute("data-uses", id); else root.removeAttribute("data-uses");
  };
  // The menu's rows: the app's /open for an app this browser has used (Herd Planner's older one-word memory
  // counts too), else the page here. The page is kept in data-page, so the row can go back to it.
  var rows = function () {
    var used = opened(), id = read();
    if (id && menuApps.indexOf(id) > -1 && used.indexOf(id) < 0) used.push(id);
    var links = document.querySelectorAll("a[data-open][data-app]");
    for (var i = 0; i < links.length; i++) {
      var a = links[i], page = a.getAttribute("data-page") || a.getAttribute("href");
      a.setAttribute("data-page", page);
      a.setAttribute("href", used.indexOf(a.getAttribute("data-app")) > -1 ? a.getAttribute("data-open") : page);
    }
  };
  var redraw = function () { show(); rows(); };
  var arrive = function () {
    var mark = /^#(uses|left)=([a-z0-9-]{1,40})$/.exec(location.hash);
    if (mark && (apps.indexOf(mark[2]) > -1 || menuApps.indexOf(mark[2]) > -1)) {
      if (apps.indexOf(mark[2]) > -1) {
        if (mark[1] === "uses") write(mark[2]); else if (read() === mark[2]) write(null);
      }
      if (menuApps.indexOf(mark[2]) > -1) {
        var list = opened().filter(function (id) { return id !== mark[2]; });
        keep(mark[1] === "uses" ? list.concat(mark[2]) : list);
      }
      // The mark has done its job: take it out of the address so it isn't bookmarked or shared.
      try { history.replaceState(null, "", location.pathname + location.search); } catch (e) { /* fine */ }
    }
    redraw();
  };
  arrive();
  document.addEventListener("DOMContentLoaded", rows);   // the menu is drawn after this script runs
  window.addEventListener("hashchange", arrive);   // the same tab, already on this site, sent here again
  // A tab that was already open, or one brought back with the Back button, catches up with the others.
  window.addEventListener("storage", function (ev) { if (ev.key === KEY || ev.key === OPEN || ev.key === null) redraw(); });
  window.addEventListener("pageshow", redraw);
  // "Forget this": back to what a new visitor sees.
  document.addEventListener("click", function (ev) {
    var button = ev.target && ev.target.closest ? ev.target.closest("[data-forget-app]") : null;
    if (!button) return;
    ev.preventDefault();
    write(null);
    keep([]);
    redraw();
    if (button.getAttribute("data-done")) { button.textContent = button.getAttribute("data-done"); button.disabled = true; }
    // The button's own line may have just gone with the rest: hand the keyboard to the first sign-up link
    // rather than leave it nowhere.
    if (!button.getClientRects().length) {
      var next = document.querySelector("main a.visitor-only") || document.querySelector(".site-nav .nav-visitor");
      if (next) next.focus();
    }
  });
})();
