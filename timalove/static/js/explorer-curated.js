/**
 * TimaLove — Parcours curated : chargement infini + statut en ligne
 * + retrait / remplacement après like.
 */
(function () {
  const grid = document.getElementById("curated-list-grid");
  const sentinel = document.getElementById("curated-scroll-sentinel");
  const loader = document.querySelector("[data-curated-loader]");
  if (!grid) return;

  const ONLINE_POLL_MS = 12000;
  const LOAD_DELAY_MS = 2000;
  let loading = false;
  let observer = null;

  function csrf() {
    const m = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  function setLoader(on) {
    if (!loader) return;
    loader.hidden = !on;
  }

  function applyOnlineDot(card, isOn) {
    card.setAttribute("data-online", isOn ? "1" : "0");
    const media = card.querySelector(".curated-card__media");
    if (media) {
      let dot = media.querySelector(".curated-card__online");
      if (isOn) {
        if (!dot) {
          dot = document.createElement("i");
          dot.className = "curated-card__online";
          dot.setAttribute("aria-label", "En ligne");
          media.appendChild(dot);
        }
      } else if (dot) {
        dot.remove();
      }
    }
    const place = card.querySelector(".curated-card__place");
    if (!place) return;
    let live = place.querySelector(".curated-card__live");
    if (isOn) {
      if (!live) {
        live = document.createElement("span");
        live.className = "curated-card__live";
        live.textContent = "En ligne";
        place.insertBefore(live, place.firstChild);
      }
    } else if (live) {
      live.remove();
    }
  }

  function syncOnlineDots() {
    if (document.body.classList.contains("is-guest")) return;
    const cards = grid.querySelectorAll(".curated-card[data-profile-id]");
    if (!cards.length) return;
    const ids = [];
    cards.forEach(function (card) {
      const id = card.getAttribute("data-profile-id");
      if (id) ids.push(id);
    });
    if (!ids.length) return;

    fetch("/api/profiles/online/?ids=" + encodeURIComponent(ids.join(",")), {
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (res) {
        if (!res.ok) throw new Error("online");
        return res.json();
      })
      .then(function (data) {
        const online = (data && data.online) || {};
        cards.forEach(function (card) {
          const id = card.getAttribute("data-profile-id");
          applyOnlineDot(card, !!online[id]);
        });
      })
      .catch(function () {});
  }

  window.timaloveSyncCuratedOnline = syncOnlineDots;
  document.addEventListener("timalove:presence", function (event) {
    const detail = (event && event.detail) || {};
    const profileId = String(detail.profile_id || "");
    if (!profileId) return;
    const card = grid.querySelector('.curated-card[data-profile-id="' + profileId + '"]');
    if (card) applyOnlineDot(card, !!detail.online);
  });
  syncOnlineDots();
  window.setInterval(syncOnlineDots, ONLINE_POLL_MS);

  function showEmptyState() {
    const section = grid.closest(".curated-list");
    if (!section || grid.querySelector(".curated-card")) return;
    if (section.querySelector(".curated-list__empty")) return;
    const empty = document.createElement("div");
    empty.className = "curated-list__empty";
    empty.innerHTML =
      "<h2>Aucun profil compatible aujourd'hui</h2><p>Revenez demain ou ajustez vos filtres de découverte.</p>";
    grid.remove();
    if (sentinel) sentinel.hidden = true;
    setLoader(false);
    section.appendChild(empty);
  }

  function applySentinel(node) {
    if (!sentinel) return;
    if (!node) {
      sentinel.hidden = true;
      sentinel.setAttribute("data-has-more", "0");
      return;
    }
    const has = node.getAttribute("data-has-more") === "1" && !node.hidden;
    sentinel.setAttribute("data-has-more", has ? "1" : "0");
    sentinel.hidden = !has;
  }

  function hasMore() {
    return !!(sentinel && !sentinel.hidden && sentinel.getAttribute("data-has-more") === "1");
  }

  function appendCardsFromHtml(html) {
    if (!html || !html.trim()) {
      applySentinel(null);
      return;
    }
    const tmp = document.createElement("div");
    tmp.innerHTML = html.trim();
    tmp.querySelectorAll(".curated-card").forEach(function (node) {
      if (grid.querySelector('.curated-card[data-profile-id="' + node.getAttribute("data-profile-id") + '"]')) {
        return;
      }
      grid.appendChild(node);
    });
    applySentinel(tmp.querySelector("#curated-scroll-sentinel"));
    syncOnlineDots();
  }

  function wait(ms) {
    return new Promise(function (resolve) {
      window.setTimeout(resolve, ms);
    });
  }

  function loadMore() {
    if (loading || !hasMore()) return;
    loading = true;
    setLoader(true);
    const started = Date.now();
    fetch("/explorer/curated-plus/", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "X-CSRFToken": csrf(),
        "HX-Request": "true",
        "X-Requested-With": "XMLHttpRequest",
      },
    })
      .then(function (res) {
        if (!res.ok) throw new Error("Chargement impossible.");
        return res.text();
      })
      .then(function (html) {
        const remain = Math.max(0, LOAD_DELAY_MS - (Date.now() - started));
        return wait(remain).then(function () {
          return html;
        });
      })
      .then(function (html) {
        if (!html.trim()) {
          applySentinel(null);
          return;
        }
        appendCardsFromHtml(html);
      })
      .catch(function () {})
      .finally(function () {
        setLoader(false);
        loading = false;
      });
  }

  function replaceConsumed(profileId) {
    const card = grid.querySelector('.curated-card[data-profile-id="' + profileId + '"]');
    if (card) card.remove();
    fetch("/explorer/curated-replace/", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf(),
        "X-Requested-With": "XMLHttpRequest",
        "HX-Request": "true",
      },
      body: JSON.stringify({ profile_id: profileId }),
    })
      .then(function (res) {
        if (!res.ok) throw new Error("replace");
        return res.text();
      })
      .then(function (html) {
        appendCardsFromHtml(html);
        if (!grid.querySelector(".curated-card")) {
          showEmptyState();
        }
      })
      .catch(function () {
        if (!grid.querySelector(".curated-card")) {
          showEmptyState();
        }
      });
  }

  document.addEventListener("timalove:swipe", function (event) {
    const detail = (event && event.detail) || {};
    if (detail.action !== "like" && detail.action !== "super_like") return;
    const profileId = String(detail.profileId || "");
    if (!profileId) return;
    replaceConsumed(profileId);
  });

  if (sentinel && "IntersectionObserver" in window) {
    observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) loadMore();
        });
      },
      { root: null, rootMargin: "280px 0px", threshold: 0 }
    );
    observer.observe(sentinel);
  }
})();
