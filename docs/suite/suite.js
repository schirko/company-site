/* Farm app suite: the "Farm Apps" menu in each app's header. Suite version 2.
   THE SAME FILE lives in Herd Planner and Farm Equipment Planner; the master copy
   is herd-planner/brand/suite.js (a test in each app fails if its copy drifts).

   Markup: <details class="suite-apps" data-suite-apps="<this app's id>" data-suite-base="<folder>">
   - If the <details> is empty, the menu is built from <folder>/suite-apps.json
     (Herd Planner does this; its pages are plain HTML).
   - If it is already filled in (the Equipment Planner's Django template does
     that on the server), this script only adds the closing behavior.
   The menu is a <details> element, so it opens and closes even without JavaScript. */
(function () {
  "use strict";

  function el(tag, attrs, text) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs || {})) node.setAttribute(key, value);
    if (text) node.textContent = text;
    return node;
  }

  function build(menu, list) {
    const here = menu.dataset.suiteApps;
    const base = menu.dataset.suiteBase || ".";
    menu.appendChild(el("summary", { "aria-label": "Our Farm Apps" }, "Farm Apps"));
    const panel = el("div", { class: "suite-apps-panel" });
    panel.appendChild(el("p", { class: "suite-apps-title" }, "Our Farm Apps"));
    for (const app of list.apps) {
      const isHere = app.id === here;
      const row = app.url && !isHere ? el("a", { class: "suite-app", href: app.url }) : el("div", { class: "suite-app" });
      if (isHere) row.classList.add("here");
      row.appendChild(el("img", { src: `${base}/suite-logos/${app.id}.svg`, alt: "", width: "36", height: "36" }));
      const words = el("span", { class: "suite-app-words" });
      words.appendChild(el("strong", {}, app.name));
      words.appendChild(el("span", {}, app.what));
      row.appendChild(words);
      row.appendChild(el("span", { class: "suite-app-status" }, isHere ? "You're here" : app.url ? "Open" : "Coming soon"));
      panel.appendChild(row);
    }
    menu.appendChild(panel);
  }

  function closeOnOutsideClickOrEscape(menu) {
    document.addEventListener("click", (event) => { if (menu.open && !menu.contains(event.target)) menu.open = false; });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && menu.open) { menu.open = false; menu.querySelector("summary").focus(); }
    });
  }

  for (const menu of document.querySelectorAll("details.suite-apps")) {
    closeOnOutsideClickOrEscape(menu);
    if (menu.children.length) continue;               // filled in on the server
    const base = menu.dataset.suiteBase || ".";
    fetch(`${base}/suite-apps.json`)
      .then((response) => (response.ok ? response.json() : Promise.reject(response.status)))
      .then((list) => build(menu, list))
      .catch(() => menu.remove());                     // no list (offline, first visit): no menu rather than a broken one
  }
})();
