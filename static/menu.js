/* The Our Farm Apps menu in the header (a <details> element, so it opens without JavaScript).
   This adds what a menu should do: close on a click elsewhere, on Escape, and when a link is chosen. */
(function () {
  "use strict";
  document.addEventListener("DOMContentLoaded", () => {
    const menu = document.querySelector("details[data-mega]");
    // The phone's Menu (2026-10-13): the header's links as a white list. A chosen link, a tap outside the header,
    // Escape or turning the phone sideways closes it. Our Farm Apps opens its list in place inside it.
    const btn = document.getElementById("menu-btn");
    const header = btn && btn.closest("header");
    let flat = false;
    const setMenu = (open) => {
      if (!btn) return;
      flat = open;
      header.classList.toggle("menu-open", open);
      btn.setAttribute("aria-expanded", String(open));
      if (!open && menu) menu.open = false;
    };
    if (btn) btn.addEventListener("click", (e) => { e.stopPropagation(); setMenu(!flat); });
    const phone = typeof window.matchMedia === "function" ? window.matchMedia("(max-width: 640px)") : null;
    if (phone && phone.addEventListener) phone.addEventListener("change", () => { if (!phone.matches && flat) setMenu(false); });
    document.addEventListener("click", (e) => {
      if (flat) {
        if (!header.contains(e.target) || (e.target.closest("#site-nav a"))) setMenu(false);
        return;
      }
      if (menu && menu.open && !menu.contains(e.target)) menu.open = false;
    });
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Escape") return;
      if (flat) { setMenu(false); btn.focus(); return; }
      if (menu && menu.open) { menu.open = false; menu.querySelector("summary").focus(); }
    });
    if (menu) menu.querySelector(".mega-panel").addEventListener("click", (e) => { if (e.target.closest("a")) menu.open = false; });
  });
})();
