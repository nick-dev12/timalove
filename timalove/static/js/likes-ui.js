/**
 * TimaLove — page Likes (filtres + like / super like / pass via API).
 */
(function () {
  function cookie(name) {
    const m = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return m ? decodeURIComponent(m[1]) : "";
  }

  function csrf() {
    const fromCookie = cookie("csrftoken");
    if (fromCookie) return fromCookie;
    const input = document.querySelector("[name=csrfmiddlewaretoken]");
    return input ? input.value : "";
  }

  function postSwipe(profileId, action) {
    return fetch("/api/swipes/", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify({ swiped_id: profileId, action: action }),
    }).then(function (res) {
      const ct = res.headers.get("content-type") || "";
      if (!ct.includes("application/json")) {
        throw new Error("Impossible d'enregistrer.");
      }
      return res.json().then(function (data) {
        return { ok: res.ok, data: data };
      });
    });
  }

  function showError(message) {
    let toast = document.getElementById("swipe-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "swipe-toast";
      toast.className = "swipe-toast";
      toast.setAttribute("role", "status");
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.hidden = false;
    window.clearTimeout(showError._timer);
    showError._timer = window.setTimeout(function () {
      toast.hidden = true;
    }, 3200);
  }

  function profileIdFrom(el) {
    const card = el.closest("[data-profile-id]");
    return card ? card.getAttribute("data-profile-id") : null;
  }

  function setPressed(btn, on, labelOn, labelOff) {
    if (!btn) return;
    btn.setAttribute("aria-pressed", on ? "true" : "false");
    btn.classList.toggle("is-on", on);
    if (labelOn && labelOff && btn.classList.contains("likes__btn--primary")) {
      btn.textContent = on ? labelOn : labelOff;
    }
  }

  function hideCard(card, root, applyFilter) {
    if (!card) return;
    card.classList.add("is-gone");
    card.hidden = true;
    const active = root.querySelector("[data-likes-filter].is-on");
    applyFilter((active && active.getAttribute("data-likes-filter")) || "all");
  }

  document.addEventListener("DOMContentLoaded", function () {
    const root = document.querySelector("[data-likes-root]");
    if (!root) return;

    if (typeof window.timaloveRenderLikesBadge === "function") {
      window.timaloveRenderLikesBadge(0);
    }

    const filters = root.querySelectorAll("[data-likes-filter]");
    const empty = root.querySelector(".likes__empty-filter");
    const isLive = root.getAttribute("data-likes-live") === "1";

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

    const feedWrap = root.querySelector("[data-likes-feed]");
    if (feedWrap && isLive) {
      const feedUrl = feedWrap.getAttribute("data-feed-url") || "/likes/feed/";
      function refreshFeed() {
        if (document.hidden) return;
        fetch(feedUrl, {
          credentials: "same-origin",
          headers: { "X-Requested-With": "XMLHttpRequest" },
        })
          .then(function (res) {
            if (!res.ok) throw new Error("feed");
            return res.text();
          })
          .then(function (html) {
            if (!html || !html.trim()) return;
            feedWrap.innerHTML = html;
            const countEl = root.querySelector("[data-likes-count]");
            const countNode = feedWrap.querySelector("[data-likes-count-value]");
            if (countEl && countNode) {
              const n = parseInt(countNode.getAttribute("data-likes-count-value") || "0", 10);
              countEl.textContent = n + (n > 1 ? " profils" : n === 1 ? " profil" : " profil");
            }
            const active = root.querySelector("[data-likes-filter].is-on");
            applyFilter((active && active.getAttribute("data-likes-filter")) || "all");
          })
          .catch(function () {});
      }
      window.setInterval(refreshFeed, 15000);
      document.addEventListener("timalove:likes-refresh", refreshFeed);
      document.addEventListener("visibilitychange", function () {
        if (!document.hidden) refreshFeed();
      });
      window.addEventListener("focus", refreshFeed);
    }

    root.addEventListener("click", function (event) {
      const pass = event.target.closest("[data-likes-pass]");
      if (pass) {
        const card = pass.closest("[data-filter-item]");
        if (!isLive) {
          hideCard(card, root, applyFilter);
          return;
        }
        const id = profileIdFrom(pass);
        if (!id || pass.disabled || pass.classList.contains("is-busy")) return;
        pass.classList.add("is-busy");
        postSwipe(id, "pass")
          .then(function (_ref) {
            var ok = _ref.ok;
            var data = _ref.data;
            if (!ok || !data.ok) throw new Error((data && data.error) || "Impossible d'enregistrer.");
            hideCard(card, root, applyFilter);
          })
          .catch(function (err) {
            showError(err && err.message ? err.message : "Impossible d'enregistrer.");
          })
          .finally(function () {
            pass.classList.remove("is-busy");
          });
        return;
      }

      const back = event.target.closest("[data-likes-back]");
      if (back) {
        if (!isLive) {
          const on = back.getAttribute("aria-pressed") === "true";
          setPressed(back, !on, "Aimé", "Liker en retour");
          return;
        }
        const id = profileIdFrom(back);
        if (!id || back.disabled || back.classList.contains("is-busy")) return;
        back.classList.add("is-busy");
        postSwipe(id, "like")
          .then(function (_ref2) {
            var ok = _ref2.ok;
            var data = _ref2.data;
            if (!ok || !data.ok) throw new Error((data && data.error) || "Impossible d'enregistrer.");
            setPressed(back, true, "Aimé", "Liker en retour");
            if (data.matched && data.match_id) {
              window.setTimeout(function () {
                window.location.href = "/discussions/" + id + "/";
              }, 900);
            }
          })
          .catch(function (err) {
            showError(err && err.message ? err.message : "Impossible d'enregistrer.");
          })
          .finally(function () {
            back.classList.remove("is-busy");
          });
        return;
      }

      const superBtn = event.target.closest("[data-likes-super]");
      if (superBtn) {
        if (!isLive) {
          setPressed(superBtn, true);
          return;
        }
        const id = profileIdFrom(superBtn);
        if (!id || superBtn.disabled || superBtn.classList.contains("is-busy")) return;
        superBtn.classList.add("is-busy");
        postSwipe(id, "super_like")
          .then(function (_ref3) {
            var ok = _ref3.ok;
            var data = _ref3.data;
            if (!ok || !data.ok) throw new Error((data && data.error) || "Impossible d'enregistrer.");
            setPressed(superBtn, true);
            const card = superBtn.closest("[data-filter-item]");
            if (card) card.setAttribute("data-super", "1");
            if (data.matched && data.match_id) {
              window.setTimeout(function () {
                window.location.href = "/discussions/" + id + "/";
              }, 900);
            }
          })
          .catch(function (err) {
            showError(err && err.message ? err.message : "Impossible d'enregistrer.");
          })
          .finally(function () {
            superBtn.classList.remove("is-busy");
          });
      }
    });
  });
})();
