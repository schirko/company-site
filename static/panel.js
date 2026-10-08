/* "See your county": lets a visitor swap the live panel's tiles to their own county, and pick their sale barn.

   The page itself always shows the county of the week (that's what search engines and first-time
   visitors see). When someone picks a county, this script loads panel-data.json (every county's
   tiles, drawn in advance by build.py with the same code as the page) and swaps three tiles and the
   heading, plus the three figures pinned on the photo at the top of the page. The choices are kept in this browser only (localStorage), so the next visit opens on their
   county. Nothing is sent anywhere; there is no account and no location lookup.

   The steer tile by barn (October 2026, format 3 of panel-data.json): a county's tile names the nearest barn
   with a fresh price (a sale in the last three weeks, by the visitor's own date, since a price can age out
   during the week). A barn the visitor chose is never swapped for another: if it hasn't sold lately the tile
   says so and lists the nearest barns that have. This is cards.choose in the browser; keep the two alike.

   Without JavaScript the picker stays hidden and the page works as before. */
(function () {
  "use strict";

  const KEY = "panel-county";
  const BARN_KEY = "panel-barn";
  const panel = document.getElementById("this-week");
  if (!panel) return;
  const openButton = panel.querySelector(".live-pick-open");
  const form = panel.querySelector(".live-pick");
  const stateSelect = form.elements.namedItem("state");
  const countySelect = form.elements.namedItem("county");
  const barnSelect = form.elements.namedItem("barn");
  const title = panel.querySelector(".live-title");
  const where = panel.querySelector(".live-where");
  const original = {};                       // the county of the week's tiles, to put back
  for (const slot of ["herd", "corn", "days"]) {
    const tile = panel.querySelector(`[data-tile="${slot}"]`);
    if (tile) original[slot] = tile.outerHTML;
  }
  const originalWhere = where.textContent;
  // The three figures pinned on the photo follow the picked county too (the home page only).
  const pins = document.getElementById("pins");
  const pinsWhere = pins && pins.querySelector(".pins-where");
  const originalPins = {};
  if (pins) for (const pin of pins.querySelectorAll("[data-pin]")) originalPins[pin.dataset.pin] = pin.outerHTML;
  const originalPinsWhere = pinsWhere ? pinsWhere.textContent : "";
  let data = null;

  // The button after the county's name: "See your county" until a visitor picks one, then "Change" (a screen
  // reader hears "Change county": the name it changes is right before it, but a lone "Change" says too little).
  function label(yours) {
    openButton.textContent = yours ? "Change" : "See your county";
    if (yours) openButton.setAttribute("aria-label", "Change county"); else openButton.removeAttribute("aria-label");
  }

  // localStorage can be missing or refuse (private windows, blocked site data): never let that break the page.
  const store = (key, value) => { try { value ? localStorage.setItem(key, value) : localStorage.removeItem(key); } catch (e) { /* fine */ } };
  const stored = (key) => { try { return localStorage.getItem(key); } catch (e) { return null; } };
  const remember = (fips) => store(KEY, fips);
  const remembered = () => stored(KEY);

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

  function swapPin(slot, html) {
    const pin = pins && pins.querySelector(`[data-pin="${slot}"]`);
    if (!pin || !html) return;
    const holder = document.createElement("div");
    holder.innerHTML = html.trim();
    pin.replaceWith(holder.firstElementChild);
  }

  // "Change barn" links are drawn hidden (they need this script): show them.
  const showChangeLinks = () => { for (const a of panel.querySelectorAll("[data-change-barn]")) a.hidden = false; };

  // --- the steer tile by barn ---------------------------------------------------------------------

  function isFresh(iso) {                    // a sale in the last fresh_days days, by this visitor's date
    const sold = Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10));
    const now = new Date();
    const today = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
    return (today - sold) / 86400000 <= data.fresh_days;
  }

  // [tile, pin] for a county, or null when the data has no barn positions (then the state's tile is used).
  function steer(c) {
    if (!data.barns || !c.barns) return null;
    const B = data.barns;
    const fresh = c.barns.map((x) => x[0]).filter((s) => B[s] && isFresh(B[s].last_sale));
    const hub = data.hub && B[data.hub];
    const chosen = stored(BARN_KEY);
    if (chosen && B[chosen]) {
      const b = B[chosen];
      if (isFresh(b.last_sale)) return [b.tile, b.pin];
      let rows = fresh.filter((s) => s !== chosen).slice(0, 2).map((s) => B[s].row);
      let head = data.near_head.near;
      if (!rows.length && hub && data.hub !== chosen && isFresh(hub.last_sale)) { rows = [hub.row]; head = data.near_head.benchmark; }
      const near = rows.length ? `<span class="near"><span class="near-head">${head}</span>${rows.join("")}</span>` : "";
      return [b.quiet.replace(data.near_token, near), b.quiet_pin];
    }
    if (fresh.length) return [B[fresh[0]].tile, B[fresh[0]].pin];
    if (hub && isFresh(hub.last_sale)) return [hub.bench_tile, hub.bench_pin];
    return [data.none_tile, data.none_pin];
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

  // The barns within 250 miles of the county, nearest first; a chosen barn farther away stays in the list.
  function fillBarns(fips, selected) {
    const label = barnSelect.closest("label");
    const c = data.counties[fips];
    if (!data.barns || !c || !c.barns) { label.hidden = true; return; }
    label.hidden = false;
    const B = data.barns;
    const options = [new Option("Nearest with a fresh price", "")];
    for (const [slug, mi] of c.barns) {
      if (!B[slug]) continue;
      const quiet = isFresh(B[slug].last_sale) ? "" : ", no recent sale";   // the list says it before the tile does
      options.push(new Option(`${B[slug].city}, ${B[slug].state} (${mi} mi${quiet})`, slug));
    }
    if (selected && B[selected] && !c.barns.some((x) => x[0] === selected)) {
      options.push(new Option(`${B[selected].city}, ${B[selected].state}`, selected));
    }
    barnSelect.replaceChildren(...options);
    barnSelect.value = selected && B[selected] ? selected : "";
  }

  function show(fips) {
    const c = data.counties[fips];
    if (!c) return false;
    const s = steer(c);
    swap("herd", s ? s[0] : data.herd[c.state]);
    swap("corn", c.corn);
    swap("days", c.days);
    swapPin("herd", s ? s[1] : (data.herd_pin || {})[c.state]);
    swapPin("land", (c.pins || {}).land);
    swapPin("corn", (c.pins || {}).corn);
    if (pinsWhere) pinsWhere.textContent = `${c.name}, ${data.states[c.state]}`;
    title.textContent = "Your County";
    where.textContent = `${c.name}, ${data.states[c.state]}`;
    panel.classList.add("is-yours");
    showChangeLinks();
    return true;
  }

  function reset() {
    for (const [slot, html] of Object.entries(original)) swap(slot, html);
    for (const [slot, html] of Object.entries(originalPins)) swapPin(slot, html);
    if (pinsWhere) pinsWhere.textContent = originalPinsWhere;
    title.textContent = "This Week";
    where.textContent = originalWhere;
    panel.classList.remove("is-yours");
    showChangeLinks();
  }

  function openForm(open, focus) {
    form.hidden = !open;
    openButton.setAttribute("aria-expanded", String(open));
    if (open) (focus || stateSelect).focus();
  }

  // Open the picker on the visitor's county (or the county of the week). toBarn: from "Change barn", so the
  // picker opens (never closes) with the barn list focused.
  function startPicker(toBarn) {
    load().then(() => {
      const fips = remembered() || data.default;
      const state = (data.counties[fips] || {}).state || Object.keys(data.states)[0];
      fillStates();
      stateSelect.value = state;
      fillCounties(state, fips);
      fillBarns(countySelect.value, stored(BARN_KEY));
      const barnShown = !barnSelect.closest("label").hidden;
      openForm(toBarn ? true : form.hidden, toBarn && barnShown ? barnSelect : null);
    }).catch(() => { openButton.hidden = true; });   // no data file: quietly no picker
  }

  openButton.hidden = false;
  showChangeLinks();
  openButton.addEventListener("click", () => startPicker(false));
  panel.addEventListener("click", (event) => {
    const link = event.target.closest && event.target.closest("[data-change-barn]");
    if (!link) return;
    event.preventDefault();
    startPicker(true);
  });
  stateSelect.addEventListener("change", () => { fillCounties(stateSelect.value); fillBarns(countySelect.value, barnSelect.value); });
  countySelect.addEventListener("change", () => fillBarns(countySelect.value, barnSelect.value));
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    store(BARN_KEY, barnSelect.closest("label").hidden ? null : barnSelect.value || null);
    if (show(countySelect.value)) { remember(countySelect.value); label(true); openForm(false); }
  });
  form.querySelector(".live-pick-reset").addEventListener("click", () => {
    remember(null); store(BARN_KEY, null); reset(); label(false); openForm(false);
  });

  // A returning visitor: open on their county (and their barn).
  const saved = remembered();
  if (saved) {
    load().then(() => { if (show(saved)) label(true); }).catch(() => {});
  }
})();
