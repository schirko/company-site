/* "See your county": lets a visitor swap the live panel's tiles to their own county.

   The page itself always shows the county of the week (that's what search engines and first-time
   visitors see). When someone picks a county, this script loads panel-data.json (every county's
   tiles, drawn in advance by build.py with the same code as the page) and swaps three tiles and the
   heading. The choice is kept in this browser only (localStorage), so the next visit opens on their
   county. Nothing is sent anywhere; there is no account and no location lookup.

   Without JavaScript the picker stays hidden and the page works as before. */
(function () {
  "use strict";

  const KEY = "panel-county";
  const panel = document.getElementById("this-week");
  if (!panel) return;
  const openButton = panel.querySelector(".live-pick-open");
  const form = panel.querySelector(".live-pick");
  const stateSelect = form.elements.namedItem("state");
  const countySelect = form.elements.namedItem("county");
  const title = panel.querySelector(".live-title");
  const where = panel.querySelector(".live-where");
  const original = {};                       // the county of the week's tiles, to put back
  for (const slot of ["herd", "corn", "days"]) {
    const tile = panel.querySelector(`[data-tile="${slot}"]`);
    if (tile) original[slot] = tile.outerHTML;
  }
  const originalWhere = where.textContent;
  let data = null;

  // localStorage can be missing or refuse (private windows, blocked site data): never let that break the page.
  const remember = (fips) => { try { fips ? localStorage.setItem(KEY, fips) : localStorage.removeItem(KEY); } catch (e) { /* fine */ } };
  const remembered = () => { try { return localStorage.getItem(KEY); } catch (e) { return null; } };

  function load() {
    if (data) return Promise.resolve(data);
    return fetch("panel-data.json").then((r) => (r.ok ? r.json() : Promise.reject(r.status))).then((d) => (data = d));
  }

  function swap(slot, html) {
    const tile = panel.querySelector(`[data-tile="${slot}"]`);
    if (!tile || !html) return;
    const holder = document.createElement("div");
    holder.innerHTML = html.trim();          // drawn by build.py from our own data, already escaped
    tile.replaceWith(holder.firstElementChild);
  }

  function fillStates() {
    stateSelect.replaceChildren(...Object.entries(data.states).map(([code, name]) => new Option(name, code)));
  }

  function fillCounties(state, selected) {
    const rows = Object.entries(data.counties).filter(([, c]) => c.state === state)
      .sort((a, b) => a[1].name.localeCompare(b[1].name));
    countySelect.replaceChildren(...rows.map(([fips, c]) => new Option(c.name, fips)));
    if (selected) countySelect.value = selected;
  }

  function show(fips) {
    const c = data.counties[fips];
    if (!c) return false;
    swap("herd", data.herd[c.state]);
    swap("corn", c.corn);
    swap("days", c.days);
    title.textContent = "Your County";
    where.textContent = `${c.name}, ${data.states[c.state]}`;
    panel.classList.add("is-yours");
    return true;
  }

  function reset() {
    for (const [slot, html] of Object.entries(original)) swap(slot, html);
    title.textContent = "This Week";
    where.textContent = originalWhere;
    panel.classList.remove("is-yours");
  }

  function openForm(open) {
    form.hidden = !open;
    openButton.setAttribute("aria-expanded", String(open));
    if (open) stateSelect.focus();
  }

  openButton.hidden = false;
  openButton.addEventListener("click", () => {
    load().then(() => {
      const fips = remembered() || data.default;
      const state = (data.counties[fips] || {}).state || Object.keys(data.states)[0];
      fillStates();
      stateSelect.value = state;
      fillCounties(state, fips);
      openForm(form.hidden);
    }).catch(() => { openButton.hidden = true; });   // no data file: quietly no picker
  });
  stateSelect.addEventListener("change", () => fillCounties(stateSelect.value));
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (show(countySelect.value)) { remember(countySelect.value); openButton.textContent = "Change county"; openForm(false); }
  });
  form.querySelector(".live-pick-reset").addEventListener("click", () => {
    remember(null); reset(); openButton.textContent = "See your county"; openForm(false);
  });

  // A returning visitor: open on their county.
  const saved = remembered();
  if (saved) {
    load().then(() => { if (show(saved)) openButton.textContent = "Change county"; }).catch(() => {});
  }
})();
