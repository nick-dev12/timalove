/**
 * TimaLove — Parcours curated : bouton « Voir plus » + statut en ligne.
 */
(function () {
  const grid = document.getElementById("curated-list-grid");
  const wrap = document.getElementById("curated-more-wrap");
  if (!grid) return;

  const ONLINE_POLL_MS = 30000;

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
  syncOnlineDots();
  window.setInterval(syncOnlineDots, ONLINE_POLL_MS);

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
