// A barn's logo (2026-10-21; claude/barn-plan.md Part 1 step 2). Scott chose A of farm-account/notes/barn-logo-*: small,
// left of the barn's name on its page, and tiny beside its name on the Barn Prices list. A barn uploads it in My Farm
// (Your Barn) and Cornerpost Logic approves the first one. This asks My Farm once which barns have a logo showing
// (no cookie, nothing about the visitor) and only then shows any: no answer, or My Farm asleep, leaves the names alone.
"use strict";
(function () {
  var holder = document.querySelector("[data-barn-logos]");
  if (!holder || typeof fetch !== "function") return;
  var origin = holder.getAttribute("data-barn-logos");
  var src = function (slug, version) {
    return origin + "/barn-logos/" + encodeURIComponent(slug) + ".png?v=" + encodeURIComponent(version);
  };
  var stop = typeof AbortController === "function" ? new AbortController() : null;
  if (stop) setTimeout(function () { stop.abort(); }, 20000);
  fetch(origin + "/barn-logos", { credentials: "omit", signal: stop ? stop.signal : undefined })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (live) {
      if (!live || typeof live !== "object") return;
      var one = document.getElementById("barn-logo");
      if (one) {
        var slug = one.getAttribute("data-barn");
        if (live[slug]) {
          var h1 = document.querySelector(".barn-title h1");
          one.alt = (h1 ? h1.textContent : "The barn's") + " logo";
          one.onload = function () { one.hidden = false; };
          one.src = src(slug, live[slug]);
        }
      }
      Array.prototype.forEach.call(document.querySelectorAll("a[data-barn]"), function (a) {
        var s = a.getAttribute("data-barn");
        if (!live[s]) return;
        var img = document.createElement("img");
        img.className = "barn-logo-mini";
        img.alt = "";
        img.width = 28;
        img.height = 28;
        img.onload = function () { a.classList.add("has-logo"); a.parentNode.insertBefore(img, a); };
        img.src = src(s, live[s]);
      });
    })
    .catch(function () { /* no logos shown */ });
})();
