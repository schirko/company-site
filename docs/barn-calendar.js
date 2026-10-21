// A barn's sale calendar on its page (2026-10-21; Scott: "B is good", farm-account/notes/barn-cal-2-B-*-2026-10-21.png).
// The barn keeps it in My Farm (its regular sale days, special sales and closings); this page asks for it when it opens
// and draws one month at a time, with Previous and Next. No cookie is sent and nothing about the visitor; no calendar
// (or My Farm asleep) leaves the box hidden. Every word goes in as text, never as HTML.
"use strict";
(function () {
  var box = document.getElementById("barn-calendar");
  if (!box || !window.fetch) return;
  var src = box.getAttribute("data-src"), name = box.getAttribute("data-name") || "the barn";
  var stop = window.AbortController ? new AbortController() : null;
  if (stop) setTimeout(function () { stop.abort(); }, 20000);   // My Farm can take a while to wake; then give up quietly
  var MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  var DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];   // Sunday first, as in the mockup Scott chose
  var make = function (tag, cls, text) { var x = document.createElement(tag); if (cls) x.className = cls; if (text) x.textContent = text; return x; };
  var pad = function (n) { return (n < 10 ? "0" : "") + n; };
  var iso = function (y, m, d) { return y + "-" + pad(m + 1) + "-" + pad(d); };
  var time = function (hhmm) {
    if (!hhmm) return "";
    var h = +hhmm.slice(0, 2), m = +hhmm.slice(3), half = h < 12 ? "am" : "pm";
    h = h % 12 || 12;
    return m ? h + ":" + pad(m) + " " + half : h + " " + half;
  };
  var runs = function (d, month) {             // month 1..12; a season may wrap the year (October to May)
    return d.first_month <= d.last_month ? month >= d.first_month && month <= d.last_month
      : month >= d.first_month || month <= d.last_month;
  };
  // What is on one day: [{kind: "sale"|"special"|"closed", short, long}]
  var on = function (cal, y, m, d) {
    var key = iso(y, m, d), out = [], closed = false;
    cal.sales.forEach(function (s) {
      if (s.sale_on !== key) return;
      if (s.kind === "closed") { closed = true; out.push({ kind: "closed", short: "Closed", long: "Closed" + (s.note ? ": " + s.note : "") }); return; }
      var t = time(s.starts);
      out.push({ kind: "special", short: s.kind_words + (t ? " " + t : ""), long: s.kind_words + (t ? ", " + t : "") + (s.note ? ". " + s.note : "") });
    });
    if (!closed) {
      var wd = (new Date(y, m, d).getDay() + 6) % 7;
      cal.days.forEach(function (r) {
        if (r.weekday !== wd || !runs(r, m + 1)) return;
        var t = time(r.starts);
        out.unshift({ kind: "sale", short: "Sale" + (t ? " " + t : ""), long: "Sale" + (t ? ", " + t : "") + (r.what ? ". " + r.what : "") });
      });
    }
    return out;
  };
  var draw = function (cal, y, m, first, last) {
    box.textContent = "";
    var head = make("div", "cal-head");
    var prev = make("button", "cal-nav", "‹ " + MONTHS[(m + 11) % 12]), next = make("button", "cal-nav", MONTHS[(m + 1) % 12] + " ›");
    prev.type = next.type = "button";
    prev.disabled = y * 12 + m <= first; next.disabled = y * 12 + m >= last;
    prev.addEventListener("click", function () { var t = y * 12 + m - 1; draw(cal, Math.floor(t / 12), t % 12, first, last); });
    next.addEventListener("click", function () { var t = y * 12 + m + 1; draw(cal, Math.floor(t / 12), t % 12, first, last); });
    var title = make("h2", "", "Sale Calendar: " + MONTHS[m] + " " + y);
    title.id = "barn-calendar-title";
    head.appendChild(title);
    var navs = make("div", "cal-navs"); navs.appendChild(prev); navs.appendChild(next); head.appendChild(navs);
    box.appendChild(head);
    var grid = make("div", "cal-grid");
    grid.setAttribute("aria-hidden", "true");          // the list below says the same for a screen reader
    DAYS.forEach(function (d) { grid.appendChild(make("div", "cal-dow", d)); });
    var lead = new Date(y, m, 1).getDay(), count = new Date(y, m + 1, 0).getDate(), today = cal.today;
    for (var i = 0; i < lead; i++) grid.appendChild(make("div", "cal-cell out"));
    var said = make("ul", "sr-only");
    for (var d = 1; d <= count; d++) {
      var items = on(cal, y, m, d), cell = make("div", "cal-cell");
      if (items.length) cell.className += " " + (items.some(function (x) { return x.kind === "closed"; }) ? "closed"
        : items.some(function (x) { return x.kind === "special"; }) ? "special" : "sale");
      if (iso(y, m, d) === today) cell.className += " today";
      cell.appendChild(make("b", "", String(d)));
      items.forEach(function (x) { cell.appendChild(make("span", "cal-what", (x.kind === "special" ? "★ " : "") + x.short)); });
      if (items.length) {
        cell.title = items.map(function (x) { return x.long; }).join("; ");
        said.appendChild(make("li", "", MONTHS[m] + " " + d + ": " + cell.title));
      }
      grid.appendChild(cell);
    }
    box.appendChild(grid);
    if (!said.children.length) said.appendChild(make("li", "", "No sales on the calendar in " + MONTHS[m] + "."));
    box.appendChild(said);
    if (cal.days.length) {
      var regular = make("p", "cal-note");
      regular.textContent = cal.days.map(function (r) {
        var season = (r.first_month === 1 && r.last_month === 12) ? "" : " (" + MONTHS[r.first_month - 1] + " to " + MONTHS[r.last_month - 1] + ")";
        return "Every " + ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][r.weekday]
          + (r.starts ? ", " + time(r.starts) : "") + (r.what ? ": " + r.what : "") + season;
      }).join(". ") + ".";
      box.appendChild(regular);
    }
    var up = new Date(cal.updated + "T12:00:00");
    box.appendChild(make("p", "cal-who", "From " + name + ", updated " + up.toLocaleDateString("en-US", { month: "short", day: "numeric" })
      + ". Sale days can change: call the barn to be sure."));
    phone();
    box.hidden = false;
  };
  // Add to My Phone's Calendar (2026-10-21; Scott: "A looks good", farm-account/notes/barn-ics-*-2026-10-21.png): one
  // button that opens the choices. The phone subscribes to My Farm's feed (calendar.ics) and keeps it current itself;
  // nothing about the visitor goes anywhere until they choose, and then only to their own calendar app.
  var panelOpen = false;
  var feed = src + ".ics", webcal = feed.replace(/^https?:/, "webcal:");
  var phone = function () {
    var row = make("div", "cal-phone");
    var btn = make("button", "cal-phone-btn", "\ud83d\udcc5 Add to My Phone\u2019s Calendar");
    btn.type = "button";
    btn.setAttribute("aria-expanded", panelOpen ? "true" : "false");
    var panel = make("div", "cal-phone-panel");
    panel.id = "cal-phone-panel";
    btn.setAttribute("aria-controls", panel.id);
    panel.hidden = !panelOpen;
    panel.appendChild(make("h3", "", "Add " + name + "\u2019s Sales to Your Phone"));
    panel.appendChild(make("p", "cal-small", "Your phone keeps them up to date by itself: new sales and closings show up as the barn adds them. Nothing about you is sent to us or the barn."));
    var opts = make("div", "cal-phone-opts");
    var apple = make("a", "cal-phone-main", "iPhone or Mac"); apple.href = webcal;
    var google = make("a", "cal-phone-main", "Google Calendar");
    google.href = "https://calendar.google.com/calendar/r?cid=" + encodeURIComponent(webcal);
    google.target = "_blank"; google.rel = "noopener";
    opts.appendChild(apple); opts.appendChild(google);
    panel.appendChild(opts);
    // Scott's live try (2026-10-21): on a phone the Google link opens the Calendar app, which can't add a calendar from
    // a link. Google only adds one on its website, so say how.
    panel.appendChild(make("p", "cal-small", "On an Android phone the Google Calendar app can\u2019t add it from a link. Open calendar.google.com in your browser (on the phone or a computer), choose Other calendars, then + and From URL, and paste the address below. It then shows in the app."));
    panel.appendChild(make("p", "cal-small", "Another calendar? Copy this address into its \u201cAdd calendar from URL\u201d or \u201cSubscribe\u201d:"));
    var copyRow = make("div", "cal-phone-copy");
    var addr = make("input", "");
    addr.value = feed; addr.readOnly = true; addr.setAttribute("aria-label", "The calendar's address");
    var copy = make("button", "", "Copy"); copy.type = "button";
    copy.addEventListener("click", function () {
      var done = function () { copy.textContent = "Copied"; };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(feed).then(done, function () { addr.select(); });
      else { addr.select(); try { document.execCommand("copy"); done(); } catch (e) { /* the address stays selected to copy by hand */ } }
    });
    copyRow.appendChild(addr); copyRow.appendChild(copy);
    panel.appendChild(copyRow);
    panel.appendChild(make("p", "cal-small", "To stop, remove the calendar in your phone\u2019s calendar settings."));
    btn.addEventListener("click", function () {
      panelOpen = !panelOpen; panel.hidden = !panelOpen; btn.setAttribute("aria-expanded", panelOpen ? "true" : "false");
    });
    row.appendChild(btn);
    box.appendChild(row);
    box.appendChild(panel);
  };
  fetch(src, { credentials: "omit", signal: stop ? stop.signal : undefined })
    .then(function (r) { return r.status === 200 ? r.json() : null; })
    .then(function (cal) {
      if (!cal || (!cal.days.length && !cal.sales.length)) return;
      var t = new Date(cal.today + "T12:00:00"), here = t.getFullYear() * 12 + t.getMonth();
      draw(cal, t.getFullYear(), t.getMonth(), here - 1, here + 12);
    })
    .catch(function () { /* no calendar shown */ });
})();
