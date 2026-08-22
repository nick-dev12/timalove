/**
 * TimaLove — calcul asynchrone du % Match par profil (explorer).
 */
(function () {
  const cache = new Map();
  const queued = new Set();
  let queue = [];
  let inflight = 0;
  const MAX_PARALLEL = 2;

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

  function applyScore(badge, score) {
    if (!badge) return;
    const label = badge.querySelector("[data-match-label]");
    badge.classList.remove("is-pending");
    badge.classList.add("is-ready");
    badge.dataset.matchReady = "1";
    badge.setAttribute("aria-label", "Compatibilité " + score + " pourcent");
    if (label) {
      label.textContent = score + "% Match";
    }
  }

  function applyPending(badge) {
    if (!badge || badge.dataset.matchReady === "1") return;
    badge.classList.add("is-pending");
    badge.classList.remove("is-ready");
    const label = badge.querySelector("[data-match-label]");
    if (label) label.textContent = "Calcul…";
    badge.setAttribute("aria-label", "Calcul de compatibilité en cours");
  }

  function pump() {
    while (inflight < MAX_PARALLEL && queue.length) {
      const job = queue.shift();
      inflight += 1;
      fetchScore(job.profileId)
        .then(function (score) {
          applyScore(job.badge, score);
        })
        .catch(function () {
          if (job.badge) {
            job.badge.classList.remove("is-pending");
            const label = job.badge.querySelector("[data-match-label]");
            if (label) label.textContent = "—";
          }
        })
        .finally(function () {
          inflight -= 1;
          queued.delete(job.profileId);
          pump();
        });
    }
  }

  function schedule(badge, priority) {
    if (!badge || badge.dataset.matchReady === "1") return;
    const slide = badge.closest(".explorer__slide");
    const profileId =
      badge.getAttribute("data-profile-id") ||
      (slide && slide.getAttribute("data-profile-id"));
    if (!profileId) return;

    if (cache.has(profileId)) {
      applyScore(badge, cache.get(profileId));
      return;
    }
    if (queued.has(profileId)) return;

    applyPending(badge);
    queued.add(profileId);
    const job = { badge: badge, profileId: profileId };
    if (priority === "high") {
      queue.unshift(job);
    } else {
      queue.push(job);
    }
    pump();
  }

  function scan(root, options) {
    const opts = options || {};
    const container = root || document;
    const badges = container.querySelectorAll("[data-match-score]:not([data-match-ready='1'])");
    badges.forEach(function (badge, index) {
      const high = opts.priority === "high" || index === 0;
      schedule(badge, high ? "high" : "normal");
    });
  }

  function scanVisible(feed) {
    if (!feed) return;
    const slides = feed.querySelectorAll(".explorer__slide");
    const top = feed.scrollTop;
    let best = 0;
    let dist = Infinity;
    slides.forEach(function (slide, i) {
      const d = Math.abs(slide.offsetTop - top);
      if (d < dist) {
        dist = d;
        best = i;
      }
    });
    for (let i = best; i < Math.min(slides.length, best + 3); i += 1) {
      const badge = slides[i].querySelector("[data-match-score]");
      if (badge) schedule(badge, i === best ? "high" : "normal");
    }
  }

  window.timaloveMatchScore = {
    scan: scan,
    scanVisible: scanVisible,
    schedule: schedule,
  };

  document.addEventListener("DOMContentLoaded", function () {
    const feed = document.getElementById("explorer-feed");
    if (!feed) return;
    scanVisible(feed);
    const observer = new MutationObserver(function () {
      scan(feed);
    });
    observer.observe(feed, { childList: true, subtree: true });
  });
})();
