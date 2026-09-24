/**
 * TimaLove — Parcours curated : bouton « Voir plus » + statut en ligne
 * + retrait / remplacement après like ou super like.
 */
(function () {
  const grid = document.getElementById("curated-list-grid");
  const wrap = document.getElementById("curated-more-wrap");
  if (!grid) return;

  const ONLINE_POLL_MS = 12000;

  function csrf() {
    const m = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  function applyOnlineDot(card, isOn) {
    card.setAttribute("data-online", isOn ? "1" : "0");
    const media = card.querySelector(".curated-card__media");
    if (!media) return;
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
    if (wrap) wrap.hidden = true;
    section.appendChild(empty);
  }

  function applyMoreWrap(htmlWrap) {
    if (!wrap) return;
    if (!htmlWrap) {
      wrap.hidden = true;
      return;
    }
    wrap.hidden = htmlWrap.hidden;
    const btn = wrap.querySelector("[data-curated-more]");
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Voir plus";
    }
  }

  function appendCardsFromHtml(html) {
    if (!html || !html.trim()) return;
    const tmp = document.createElement("div");
    tmp.innerHTML = html.trim();
    tmp.querySelectorAll(".curated-card").forEach(function (node) {
      if (grid.querySelector('.curated-card[data-profile-id="' + node.getAttribute("data-profile-id") + '"]')) {
        return;
      }
      grid.appendChild(node);
    });
    applyMoreWrap(tmp.querySelector("#curated-more-wrap"));
    syncOnlineDots();
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

  if (!wrap) return;

  wrap.addEventListener("click", function (event) {
    const btn = event.target.closest("[data-curated-more]");
    if (!btn || btn.disabled) return;
    event.preventDefault();
    btn.disabled = true;
    btn.textContent = "Chargement…";

    fetch("/explorer/curated-plus/", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "X-CSRFToken": csrf(),
        "HX-Request": "true",
      },
    })
      .then(function (res) {
        if (!res.ok) throw new Error("Chargement impossible.");
        return res.text();
      })
      .then(function (html) {
        if (!html.trim()) {
          wrap.hidden = true;
          return;
        }
        const tmp = document.createElement("div");
        tmp.innerHTML = html.trim();
        tmp.querySelectorAll(".curated-card").forEach(function (node) {
          grid.appendChild(node);
        });
        syncOnlineDots();
        const nextWrap = tmp.querySelector("#curated-more-wrap");
        if (nextWrap) {
          wrap.hidden = nextWrap.hidden;
          wrap.querySelector("[data-curated-more]").disabled = false;
          wrap.querySelector("[data-curated-more]").textContent = "Voir plus";
        } else {
          wrap.hidden = true;
        }
      })
      .catch(function () {
        btn.disabled = false;
        btn.textContent = "Voir plus";
      });
  });
})();
