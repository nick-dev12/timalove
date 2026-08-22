/**
 * TimaLove — explosion Like / Super like / Pass, puis profil suivant.
 */
(function () {
  const COUNT = 32;
  const PASS_COUNT = 14;
  const LIKE_SEL =
    ".explorer__action--like, .visit__action--like, .visit__dock-btn--primary[data-swipe='like'], [data-swipe='like'], [data-likes-back]";
  const STAR_SEL =
    ".explorer__action--star, .visit__dock-btn--ghost[data-swipe='super_like'], [data-swipe='super_like'], [data-likes-super]";
  const PASS_SVG =
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M18.3 5.7 12 12l6.3 6.3-1.4 1.4L10.6 13.4 4.3 19.7 2.9 18.3 9.2 12 2.9 5.7 4.3 4.3l6.3 6.3 6.3-6.3z"/></svg>';
  const HEART_SVG =
    '<svg viewBox="0 0 24 22" aria-hidden="true"><path fill="currentColor" d="M12 20.5C4.5 14.2 1.5 9.8 1.5 5.8 1.5 2.8 3.8 1 6.6 1c2.1 0 4 1.1 5.4 2.9C13.4 2.1 15.3 1 17.4 1c2.8 0 5.1 1.8 5.1 4.8 0 4-3 8.4-10.5 14.7z"/></svg>';
  const STAR_SVG =
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 17.3 18.2 21l-1.6-7.1L22 9.2l-7.2-.6L12 2 9.2 8.6 2 9.2l5.4 4.7L5.8 21z"/></svg>';
  const HEART_TINTS = ["#E8637A", "#E8637A", "#C4858B", "#ffffff", "#E8637A"];
  const STAR_TINTS = ["#E8637A", "#ffffff", "#C4858B", "#E8637A", "#3D2024"];
  const PASS_TINTS = ["#9B8A8E", "#6B5A5E", "#8a9199", "#5C3A3F"];

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

  function passBurstFrom(el) {
    const rect = el.getBoundingClientRect();
    const slide = el.closest(".explorer__slide");
    const layer = document.createElement("div");
    layer.className = "explorer-pass-burst";
    layer.setAttribute("aria-hidden", "true");
    layer.style.left = rect.left + rect.width / 2 + "px";
    layer.style.top = rect.top + rect.height / 2 + "px";
    document.body.appendChild(layer);

    el.classList.add("is-passing");
    window.setTimeout(() => el.classList.remove("is-passing"), 420);
    if (slide) {
      slide.classList.add("is-pass-dismiss");
      window.setTimeout(() => slide.classList.remove("is-pass-dismiss"), 520);
    }

    const ring = document.createElement("span");
    ring.className = "explorer-pass-burst__ring";
    layer.appendChild(ring);

    addPart(layer, "explorer-pass-burst__core", PASS_SVG);

    for (let i = 0; i < PASS_COUNT; i += 1) {
      const piece = addPart(layer, "explorer-pass-burst__bit", PASS_SVG);
      const spread = (Math.random() - 0.5) * 1.1;
      const angle = Math.PI + spread;
      const dist = 72 + Math.random() * 68;
      const lift = (Math.random() - 0.5) * 48;
      piece.style.setProperty("--dx", String(Math.cos(angle) * dist));
      piece.style.setProperty("--dy", String(Math.sin(angle) * dist + lift));
      piece.style.setProperty("--size", 0.55 + Math.random() * 0.65 + "rem");
      piece.style.setProperty("--rot", Math.random() * 60 - 30 + "deg");
      piece.style.setProperty("--dur", 0.62 + Math.random() * 0.22 + "s");
      piece.style.setProperty("--tint", PASS_TINTS[i % PASS_TINTS.length]);
      piece.style.animationDelay = i * 18 + "ms";
    }

    window.setTimeout(() => layer.remove(), 900);
  }

  window.timalovePassBurst = function (trigger) {
    if (!trigger || reducedMotion()) return;
    passBurstFrom(trigger);
  };

  document.addEventListener("click", (event) => {
    const star = event.target.closest(STAR_SEL);
    const like = star ? null : event.target.closest(LIKE_SEL);
    const trigger = star || like;
    if (!trigger) return;
    if (
      !trigger.hasAttribute("data-swipe") &&
      !trigger.hasAttribute("data-likes-back") &&
      !trigger.hasAttribute("data-likes-super")
    ) {
      return;
    }

    const kind = star ? "star" : "like";

    if (!reducedMotion()) {
      burstFrom(trigger, kind);
    }
  });
})();
