// The app tiles row on the home page: a row you can swipe or scroll sideways, snapping to each tile,
// with arrow buttons for a mouse. Not an auto-rotating carousel: it only moves when the visitor moves it.
// Without JavaScript the row still scrolls; the arrows just stay hidden.
"use strict";
(function () {
  for (const slider of document.querySelectorAll("[data-slider]")) {
    const row = slider.querySelector(".tiles");
    const prev = slider.querySelector(".slide-btn.prev");
    const next = slider.querySelector(".slide-btn.next");
    const step = () => {
      const tile = row.querySelector(".tile");
      const gap = parseFloat(getComputedStyle(row).columnGap) || 0;
      return tile ? tile.getBoundingClientRect().width + gap : row.clientWidth;
    };
    const update = () => {
      const max = row.scrollWidth - row.clientWidth;
      const fits = max <= 2;
      prev.hidden = fits || row.scrollLeft <= 2;
      next.hidden = fits || row.scrollLeft >= max - 2;
      slider.classList.toggle("more-right", !fits && row.scrollLeft < max - 2);
    };
    prev.addEventListener("click", () => row.scrollBy({ left: -step(), behavior: "smooth" }));
    next.addEventListener("click", () => row.scrollBy({ left: step(), behavior: "smooth" }));
    row.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    update();
  }
})();
