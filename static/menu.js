/* The Our Farm Apps menu in the header (a <details> element, so it opens without JavaScript).
   This adds what a menu should do: close on a click elsewhere, on Escape, and when a link is chosen. */
(function () {
  "use strict";
  document.addEventListener("DOMContentLoaded", () => {
    const menu = document.querySelector("details[data-mega]");
    if (!menu) return;
    document.addEventListener("click", (e) => { if (menu.open && !menu.contains(e.target)) menu.open = false; });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && menu.open) { menu.open = false; menu.querySelector("summary").focus(); }
    });
    menu.querySelector(".mega-panel").addEventListener("click", (e) => { if (e.target.closest("a")) menu.open = false; });
  });
})();
