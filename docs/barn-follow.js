// Follow This Barn (2026-10-20; claude/barn-plan.md Part 2). Scott: "have those Barn messages pushed out to users who
// have them selected as their Barn and also to accept notifications." He chose A of farm-account/notes/barn-alerts-*.
// The button starts as a plain link to My Farm (#follow/<barn>), which signs you in and asks there: that is what a
// visitor, no JavaScript or My Farm asleep gets. Signed in, this asks My Farm (same site, so its cookie goes along, as
// account.js does) whether you follow the barn: if you do, the button says Following with your email choice and a
// Change link to Your Barns; if not, the button opens a small box here whose email box starts unticked. Following is
// one yes, email a second. My Farm answers only this site; nothing about the visitor is kept by this site.
"use strict";
(function () {
  var row = document.getElementById("barn-follow");
  if (!row || typeof fetch !== "function") return;
  var origin = row.getAttribute("data-account"), barn = row.getAttribute("data-barn");
  var url = origin + "/site/barns/" + encodeURIComponent(barn) + "/follow";
  var button = document.getElementById("bf-button"), note = document.getElementById("bf-note");
  var panel = document.getElementById("bf-panel"), email = document.getElementById("bf-email");
  var said = document.getElementById("bf-said"), yes = document.getElementById("bf-yes");
  var yours = origin + "/#account/barns";

  function following(emailOn) {
    panel.hidden = true;
    button.className = "btn-follow on";
    button.href = yours;
    button.textContent = "";
    var star = document.createElement("span"); star.setAttribute("aria-hidden", "true"); star.textContent = "★";
    button.appendChild(star);
    button.appendChild(document.createTextNode(" Following"));
    button.removeAttribute("aria-expanded");
    button.onclick = null;
    note.textContent = (emailOn ? "Email on" : "Email off") + " · ";
    var change = document.createElement("a"); change.href = yours; change.textContent = "Change";
    note.appendChild(change);
  }

  function askHere() {
    button.setAttribute("role", "button");
    button.setAttribute("aria-expanded", "false");
    button.setAttribute("aria-controls", "bf-panel");
    button.onclick = function (ev) {
      ev.preventDefault();
      panel.hidden = !panel.hidden;
      button.setAttribute("aria-expanded", String(!panel.hidden));
      if (!panel.hidden) { email.checked = false; said.textContent = ""; email.focus(); }
    };
  }

  document.getElementById("bf-no").addEventListener("click", function () {
    panel.hidden = true; button.setAttribute("aria-expanded", "false"); button.focus();
  });

  yes.addEventListener("click", function () {
    yes.disabled = true; said.textContent = "";
    // A simple POST (no body, no custom headers): the browser sends it without asking first; My Farm checks Origin.
    fetch(url + "?email=" + (email.checked ? "true" : "false"), { method: "POST", credentials: "include", cache: "no-store" })
      .then(function (r) {
        if (r.status === 401) { location.href = origin + "/#follow/" + encodeURIComponent(barn); return null; }
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      })
      .then(function (answer) { if (answer && answer.following) { following(answer.email_on); button.focus(); } })
      .catch(function () { said.textContent = "That didn't go through. Try again, or use Your Barns in My Farm."; })
      .then(function () { yes.disabled = false; });
  });

  var stop = typeof AbortController === "function" ? new AbortController() : null;
  var timer = stop ? setTimeout(function () { stop.abort(); }, 20000) : null;    // My Farm may be waking up
  fetch(url, { credentials: "include", cache: "no-store", signal: stop ? stop.signal : undefined })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (answer) {
      if (!answer || answer.signed_in !== true) return;          // signed out: the link signs them in first
      if (answer.following) following(answer.email_on === true); else askHere();
    })
    .catch(function () { /* no answer: the plain link stays */ })
    .then(function () { if (timer) clearTimeout(timer); });
})();
