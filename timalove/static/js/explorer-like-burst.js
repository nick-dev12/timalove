/**
 * TimaLove — explosion Like / Super like, puis profil suivant.
 */
(function () {
  const COUNT = 32;
  const LIKE_SEL = ".explorer__action--like, .visit__action--like";
  const STAR_SEL = ".explorer__action--star, [data-swipe='super_like']";
  const HEART_SVG =
    '<svg viewBox="0 0 24 22" aria-hidden="true"><path fill="currentColor" d="M12 20.5C4.5 14.2 1.5 9.8 1.5 5.8 1.5 2.8 3.8 1 6.6 1c2.1 0 4 1.1 5.4 2.9C13.4 2.1 15.3 1 17.4 1c2.8 0 5.1 1.8 5.1 4.8 0 4-3 8.4-10.5 14.7z"/></svg>';
  const STAR_SVG =
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 17.3 18.2 21l-1.6-7.1L22 9.2l-7.2-.6L12 2 9.2 8.6 2 9.2l5.4 4.7L5.8 21z"/></svg>';
  const HEART_TINTS = ["#E8637A", "#E8637A", "#C4858B", "#ffffff", "#E8637A"];
  const STAR_TINTS = ["#E8637A", "#ffffff", "#C4858B", "#E8637A", "#3D2024"];

  function reducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function addPart(layer, className, svg) {
    const el = document.createElement("span");
    el.className = className;
    el.innerHTML = svg;
    layer.appendChild(el);
    return el;
  }

  function burstFrom(el, kind) {
    const isStar = kind === "star";
    const svg = isStar ? STAR_SVG : HEART_SVG;
    const tints = isStar ? STAR_TINTS : HEART_TINTS;
    const rect = el.getBoundingClientRect();
    const layer = document.createElement("div");
    layer.className = "explorer-burst" + (isStar ? " is-star" : "");
    layer.setAttribute("aria-hidden", "true");
    layer.style.left = rect.left + rect.width / 2 + "px";
    layer.style.top = rect.top + rect.height / 2 + "px";
    document.body.appendChild(layer);

    el.classList.add("is-bursting");
    window.setTimeout(() => el.classList.remove("is-bursting"), 480);

    const ring = document.createElement("span");
    ring.className = "explorer-burst__ring";
    layer.appendChild(ring);
    const ringSoft = document.createElement("span");
    ringSoft.className = "explorer-burst__ring explorer-burst__ring--soft";
    layer.appendChild(ringSoft);

    addPart(layer, "explorer-burst__core", svg);

    for (let i = 0; i < COUNT; i += 1) {
      const piece = addPart(layer, "explorer-burst__heart", svg);
      const ringIndex = i < 14 ? 0 : 1;
      const angle = (i / COUNT) * Math.PI * 2 + (Math.random() - 0.5) * 0.42;
      const dist = (ringIndex === 0 ? 110 : 175) + Math.random() * 95;
      const lift = 18 + Math.random() * 36;
      piece.style.setProperty("--dx", String(Math.cos(angle) * dist));
      piece.style.setProperty("--dy", String(Math.sin(angle) * dist - lift));
      piece.style.setProperty("--size", 0.85 + Math.random() * 1.35 + "rem");
      piece.style.setProperty("--rot", Math.random() * 90 - 45 + "deg");
      piece.style.setProperty("--dur", 0.95 + Math.random() * 0.35 + "s");
      piece.style.setProperty("--tint", tints[i % tints.length]);
      piece.style.animationDelay = (ringIndex === 0 ? 0 : 40) + i * 12 + "ms";
    }

    window.setTimeout(() => layer.remove(), 1500);
  }

  function goNextProfile() {
    if (window.timaloveExplorer && typeof window.timaloveExplorer.goNext === "function") {
      window.timaloveExplorer.goNext();
    }
  }

  document.addEventListener("click", (event) => {
    const star = event.target.closest(STAR_SEL);
    const like = star ? null : event.target.closest(LIKE_SEL);
    const trigger = star || like;
    if (!trigger) return;
    if (!trigger.hasAttribute("data-swipe")) return;

    const kind = star ? "star" : "like";
    const inExplorer = Boolean(trigger.closest("#explorer-feed, .explorer__slide"));

    if (!reducedMotion()) {
      burstFrom(trigger, kind);
    }

    if (inExplorer) {
      window.setTimeout(goNextProfile, reducedMotion() ? 0 : 360);
    }
  });
})();
