/**
 * TimaLove — calcul du % Match à la demande (clic sur le badge explorer).
 */
(function () {
  const cache = new Map();
  const inflight = new Set();
  const MIN_CALC_MS = 900;

  function fetchScore(profileId) {
    if (cache.has(profileId)) {
      return Promise.resolve(cache.get(profileId));
    }
    return fetch("/api/compatibility/" + profileId + "/", {
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (result) {
        if (!result.ok || !result.data.ok) {
          throw new Error((result.data && result.data.message) || "Score indisponible.");
        }
        cache.set(profileId, result.data.compatibility);
        return result.data.compatibility;
      });
  }

  function profileIdFrom(badge) {
    if (!badge) return "";
    const slide = badge.closest(".explorer__slide");
    return (
      badge.getAttribute("data-profile-id") ||
      (slide && slide.getAttribute("data-profile-id")) ||
      ""
    );
  }

  function setIdle(badge) {
    if (!badge) return;
    const label = badge.querySelector("[data-match-label]");
    badge.classList.remove("is-pending", "is-calculating", "is-ready");
    badge.classList.add("is-idle");
    badge.removeAttribute("data-match-ready");
    badge.setAttribute("aria-label", "Calculer la compatibilité");
    if (label) label.textContent = "Match ?";
  }

  function setCalculating(badge) {
    if (!badge) return;
    const label = badge.querySelector("[data-match-label]");
    badge.classList.remove("is-idle", "is-ready");
    badge.classList.add("is-pending", "is-calculating");
    badge.removeAttribute("data-match-ready");
    badge.setAttribute("aria-label", "Calcul de compatibilité en cours");
    badge.setAttribute("aria-busy", "true");
    if (label) label.textContent = "Calcul…";
  }

  function animateScore(badge, score) {
    if (!badge) return;
    const label = badge.querySelector("[data-match-label]");
    badge.classList.remove("is-pending", "is-calculating", "is-idle");
    badge.classList.add("is-ready");
    badge.dataset.matchReady = "1";
    badge.removeAttribute("aria-busy");
    badge.setAttribute("aria-label", "Compatibilité " + score + " pourcent");

    if (!label) return;

    const prefersReduced =
      window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) {
      label.textContent = score + "% Match";
      return;
    }

    const start = performance.now();
    const duration = 620;
    function frame(now) {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      const value = Math.round(score * eased);
      label.textContent = value + "% Match";
      if (t < 1) {
        window.requestAnimationFrame(frame);
      } else {
        label.textContent = score + "% Match";
      }
    }
    label.textContent = "0% Match";
    window.requestAnimationFrame(frame);
  }

  function setError(badge) {
    if (!badge) return;
    const label = badge.querySelector("[data-match-label]");
    badge.classList.remove("is-calculating", "is-ready");
    badge.classList.add("is-idle", "is-pending");
    badge.removeAttribute("data-match-ready");
    badge.removeAttribute("aria-busy");
    badge.setAttribute("aria-label", "Compatibilité indisponible, réessayez");
    if (label) label.textContent = "Réessayer";
  }

  function calculate(badge) {
    if (!badge || badge.dataset.matchReady === "1" || badge.classList.contains("is-calculating")) {
      return;
    }

    const profileId = profileIdFrom(badge);
    if (!profileId) return;

    if (cache.has(profileId)) {
      animateScore(badge, cache.get(profileId));
      return;
    }

    if (inflight.has(profileId)) return;
    inflight.add(profileId);

    setCalculating(badge);
    const started = performance.now();

    fetchScore(profileId)
      .then(function (score) {
        const wait = Math.max(0, MIN_CALC_MS - (performance.now() - started));
        return new Promise(function (resolve) {
          window.setTimeout(function () {
            resolve(score);
          }, wait);
        });
      })
      .then(function (score) {
        animateScore(badge, score);
      })
      .catch(function () {
        setError(badge);
      })
      .finally(function () {
        inflight.delete(profileId);
      });
  }

  function onActivate(event) {
    const badge = event.target.closest("[data-match-score]");
    if (!badge || !badge.closest("#explorer-feed")) return;
    if (badge.dataset.matchReady === "1") return;
    event.preventDefault();
    event.stopPropagation();
    calculate(badge);
  }

  document.addEventListener("click", onActivate);
  document.addEventListener("keydown", function (event) {
    if (event.key !== "Enter" && event.key !== " ") return;
    const badge = event.target.closest("[data-match-score]");
    if (!badge || !badge.closest("#explorer-feed")) return;
    event.preventDefault();
    onActivate(event);
  });

  window.timaloveMatchScore = {
    calculate: calculate,
  };
})();
