// A barn's own notice at the top of its page (2026-10-20; Scott: barns "post a current message", like "Auctions start
// at 6:00am on Saturday."). The notice lives in My Farm, where a barn sends it and Scott checks it with a call to the
// barn's listed office before it goes up; this page asks for it when it opens. No cookie is sent and nothing about the
// visitor; no notice (or My Farm asleep) leaves the box hidden. Every word goes in as text, never as HTML.
"use strict";
(function () {
  var box = document.getElementById("barn-notice");
  if (!box || !window.fetch) return;
  var src = box.getAttribute("data-src");
  var stop = window.AbortController ? new AbortController() : null;
  if (stop) setTimeout(function () { stop.abort(); }, 20000);   // My Farm can take a while to wake; then give up quietly
  var day = function (iso) {
    var d = new Date(iso + "T12:00:00");
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };
  fetch(src, { credentials: "omit", signal: stop ? stop.signal : undefined })
    .then(function (r) { return r.status === 200 ? r.json() : null; })
    .then(function (n) {
      if (!n || !n.notice) return;
      var make = function (tag, cls, text) { var x = document.createElement(tag); if (cls) x.className = cls; if (text) x.textContent = text; return x; };
      var words = make("div", "barn-notice-words");
      words.appendChild(make("small", "", "From the barn"));
      words.appendChild(make("p", "", n.notice));
      words.appendChild(make("p", "who", "Posted by " + n.by + " on " + day(n.posted) + " · shows until " + day(n.until) +
        ". We checked it came from the barn; we don’t check what it says: call the barn before you haul."));
      box.appendChild(make("span", "barn-notice-ic", "📣")).setAttribute("aria-hidden", "true");
      box.appendChild(words);
      box.hidden = false;
    })
    .catch(function () { /* no notice shown */ });
})();
