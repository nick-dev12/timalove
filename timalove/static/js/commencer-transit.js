/**
 * TimaLove — transition cœurs (commencer, connexion, inscription).
 */
(function () {
  const STORY = "Deux cœurs se cherchent…";
  const DURATION_MS = 7200;
  let started = false;

  function typewriter(typeEl, text) {
    typeEl.textContent = "";
    let i = 0;
    const step = Math.max(58, Math.floor(1600 / Math.max(text.length, 1)));
    const timer = setInterval(() => {
      i += 1;
      typeEl.textContent = text.slice(0, i);
      if (i >= text.length) clearInterval(timer);
    }, step);
  }

  function go(href) {
    window.location.href = href || "/connexion/";
  }

  function start(href) {
    const target = href || "/connexion/";
    if (started) return;
    started = true;

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      go(target);
      return;
    }

    const overlay = document.getElementById("commencer-transit");
    const typeEl = document.getElementById("commencer-transit-type");
    if (!overlay || !typeEl) {
      go(target);
      return;
    }

    overlay.hidden = false;
    overlay.removeAttribute("hidden");
    document.body.classList.add("is-commencer-transit");
    overlay.classList.add("is-active");
    typewriter(typeEl, STORY);
    window.setTimeout(() => overlay.classList.add("is-united"), 3900);
    window.setTimeout(() => go(target), DURATION_MS);
  }

  window.TimaLoveTransit = { start };

  document.addEventListener("click", (event) => {
    const cta = event.target.closest("#commencer-cta");
    if (!cta) return;
    event.preventDefault();
    start(cta.getAttribute("data-href") || "/explorer/");
  });
})();
