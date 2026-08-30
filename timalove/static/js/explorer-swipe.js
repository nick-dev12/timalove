/**
 * TimaLove — likes depuis l’explorer (feed + fiche profil modale).
 */
(function () {
  function csrf() {
    const m = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
    if (m) return decodeURIComponent(m[1]);
    const input = document.querySelector("[name=csrfmiddlewaretoken]");
    return input ? input.value : "";
  }

  function profileIdFrom(btn) {
    return (
      btn.getAttribute("data-profile-id") ||
      (btn.closest("[data-profile-id]") && btn.closest("[data-profile-id]").getAttribute("data-profile-id")) ||
      (btn.closest(".explorer__slide") && btn.closest(".explorer__slide").getAttribute("data-profile-id"))
    );
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

  function updateQuota(quota) {
    const label = document.querySelector("[data-quota-label]");
    if (!label || !quota || !quota.is_freemium) return;
    if (quota.show_explorer_quota === false) {
      label.hidden = true;
      return;
    }
    const period = quota.period_label || label.getAttribute("data-period-label") || "aujourd’hui";
    const parts = [];
    if (quota.swipes_left != null && quota.swipes_left !== "") {
      const swipes = Number(quota.swipes_left);
      parts.push(swipes + " " + (swipes > 1 ? "profils" : "profil"));
    }
    if (quota.likes_left != null && quota.likes_left !== "") {
      const likes = Number(quota.likes_left);
      const likeWord = likes > 1 ? "likes" : "like";
      const restWord = likes > 1 ? "restants" : "restant";
      parts.push(likes + " " + likeWord + " " + restWord);
    }
    if (!parts.length) {
      label.hidden = true;
      return;
    }
    label.hidden = false;
    label.textContent = parts.join(" · ") + " " + period;
  }

  function applySuccess(scope, action, data, profileId) {
    if (action === "like") {
      scope.querySelectorAll('[data-swipe="like"]').forEach(function (el) {
        el.classList.add("is-on");
        if (el.classList.contains("visit__dock-btn") || el.classList.contains("explorer__action")) {
          el.setAttribute("aria-label", "Aimé");
        }
      });
    }
    if (action === "super_like") {
      scope.querySelectorAll('[data-swipe="super_like"]').forEach(function (el) {
        el.classList.add("is-on");
      });
    }
    if (action === "like" || action === "super_like") {
      scope.querySelectorAll("[data-msg-like-required]").forEach(function (el) {
        el.removeAttribute("data-msg-like-required");
        el.setAttribute("data-msg-open", "");
        el.classList.remove("visit__action--msg-muted");
      });
    }
    if (action === "pass") {
      scope.querySelectorAll("[data-swipe]").forEach(function (el) {
        el.classList.remove("is-on");
      });
    }
    if (data.matched && data.match_id && profileId && action !== "like" && action !== "super_like") {
      window.setTimeout(function () {
        window.location.href = "/discussions/" + profileId + "/";
      }, 900);
    }
  }

  function showMessageInvite(btn, action, data, profileId) {
    if (action !== "like" && action !== "super_like") return;
    if (!window.timaloveMessageInvite || typeof window.timaloveMessageInvite.open !== "function") return;

    const slide = btn.closest(".explorer__slide");
    const scope = btn.closest(".visit, #profile-modal") || slide;
    let name = data.partner_name || "";
    let photo = data.partner_photo || "";
    if (scope) {
      if (!name) {
        const heading = scope.querySelector(".explorer__meta h2 a, .visit__name");
        if (heading) name = (heading.textContent || "").split(",")[0].trim();
      }
      if (!photo) {
        const img = scope.querySelector(".explorer__photo.is-active, .visit__hero-photo img, .visit__gallery-item img");
        if (img && img.src) photo = img.currentSrc || img.src;
      }
    }

    window.timaloveMessageInvite.open({
      profileId: profileId,
      name: name || "Membre",
      photo: photo,
      matched: Boolean(data.matched),
      action: action,
      fromExplorer: Boolean(slide && slide.closest("#explorer-feed")),
    });
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
        if (res.status === 403) throw new Error("Accès refusé. Rechargez la page puis réessayez.");
        if (res.status === 401 || res.status === 302) throw new Error("Connectez-vous pour liker.");
        throw new Error("Impossible d’enregistrer le like.");
      }
      return res.json().then(function (data) {
        return { ok: res.ok, data: data };
      });
    });
  }

  document.addEventListener("click", function (event) {
    const btn = event.target.closest("[data-swipe]");
    if (!btn) return;
    event.preventDefault();

    const id = profileIdFrom(btn);
    const action = btn.getAttribute("data-swipe");
    if (!id || !action || btn.disabled || btn.classList.contains("is-busy")) return;

    const root = btn.closest("[data-profile-id], .explorer__slide, .visit, #profile-modal") || document;

    btn.classList.add("is-busy");
    postSwipe(id, action)
      .then(function (result) {
        if (!result.ok || !result.data.ok) {
          if (result.data && result.data.quota) updateQuota(result.data.quota);
          throw new Error((result.data && result.data.error) || "Impossible d’enregistrer.");
        }
        if (result.data.quota) updateQuota(result.data.quota);
        applySuccess(root, action, result.data, id);
        if (window.timaloveExplorer && typeof window.timaloveExplorer.consume === "function") {
          window.timaloveExplorer.consume(id);
        }
        if (action === "pass") {
          if (window.timalovePassBurst) window.timalovePassBurst(btn);
        } else if (action === "like" || action === "super_like") {
          showMessageInvite(btn, action, result.data, id);
        }
        document.dispatchEvent(
          new CustomEvent("timalove:swipe", {
            detail: { profileId: id, action: action, data: result.data },
          })
        );
      })
      .catch(function (err) {
        showError(err && err.message ? err.message : "Impossible d’enregistrer.");
      })
      .finally(function () {
        btn.classList.remove("is-busy");
      });
  });
})();
