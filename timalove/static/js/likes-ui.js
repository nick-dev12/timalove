/**
 * TimaLove — page Likes (aperçu : filtres, like en retour, passer).
 */
(function () {
  document.addEventListener("DOMContentLoaded", function () {
    const root = document.querySelector("[data-likes-root]");
    if (!root) return;

    const filters = root.querySelectorAll("[data-likes-filter]");
    const empty = root.querySelector(".likes__empty-filter");

    function applyFilter(key) {
      const items = root.querySelectorAll("[data-filter-item]");
      let visible = 0;
      items.forEach(function (el) {
        if (el.classList.contains("is-gone")) return;
        const supered = el.getAttribute("data-super") === "1";
        const online = el.getAttribute("data-online") === "1";
        const show = key === "all" || (key === "super" && supered) || (key === "online" && online);
        el.hidden = !show;
        if (show) visible += 1;
      });
      if (empty) empty.hidden = visible > 0;
    }

    filters.forEach(function (btn) {
      btn.addEventListener("click", function () {
        const key = btn.getAttribute("data-likes-filter") || "all";
        filters.forEach(function (item) {
          const on = item === btn;
          item.classList.toggle("is-on", on);
          item.setAttribute("aria-selected", on ? "true" : "false");
        });
        applyFilter(key);
      });
    });

    root.addEventListener("click", function (event) {
      const pass = event.target.closest("[data-likes-pass]");
      if (pass) {
        const card = pass.closest("[data-filter-item]");
        if (!card) return;
        card.classList.add("is-gone");
        card.hidden = true;
        const active = root.querySelector("[data-likes-filter].is-on");
        applyFilter((active && active.getAttribute("data-likes-filter")) || "all");
        return;
      }
      const back = event.target.closest("[data-likes-back]");
      if (back) {
        const on = back.getAttribute("aria-pressed") === "true";
        back.setAttribute("aria-pressed", on ? "false" : "true");
        back.classList.toggle("is-on", !on);
        if (back.classList.contains("likes__btn--primary")) {
          back.textContent = on ? "Liker en retour" : "Aimé";
        }
      }
    });
  });
})();
