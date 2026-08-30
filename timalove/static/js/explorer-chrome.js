/**
 * TimaLove — menu explorer, modale profil, galerie plein écran.
 */
(function () {
  function bindMenu() {
    const btn = document.querySelector("[data-explorer-menu-btn]");
    const menu = document.getElementById("explorer-menu");
    if (!btn || !menu) return;

    function close() {
      menu.hidden = true;
      btn.setAttribute("aria-expanded", "false");
    }

    function toggle() {
      const open = menu.hidden;
      menu.hidden = !open;
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    }

    btn.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      toggle();
    });

    document.addEventListener("click", function (event) {
      if (menu.hidden) return;
      if (event.target.closest("#explorer-menu") || event.target.closest("[data-explorer-menu-btn]")) return;
      close();
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !menu.hidden) close();
    });
  }

  function bindVisitTabs(root) {
    const tabs = root.querySelectorAll("[data-visit-tabs] .visit__tab");
    if (!tabs.length) return;
    const panels = root.querySelectorAll("[data-panel]");
    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        const key = tab.getAttribute("data-tab");
        tabs.forEach(function (item) {
          const on = item === tab;
          item.classList.toggle("is-active", on);
          item.setAttribute("aria-selected", on ? "true" : "false");
        });
        panels.forEach(function (panel) {
          panel.hidden = panel.getAttribute("data-panel") !== key;
        });
      });
    });
  }

  function activateTab(root, key) {
    if (!key || !root) return;
    const tab = root.querySelector('[data-visit-tabs] .visit__tab[data-tab="' + key + '"]');
    if (tab) tab.click();
  }

  function bindLightbox() {
    const box = document.getElementById("photo-lightbox");
    if (!box) return;
    const img = box.querySelector(".photo-lightbox__img");
    const closeBtn = box.querySelector("[data-lightbox-close]");

    function closeBox() {
      box.hidden = true;
      if (img) {
        img.removeAttribute("src");
        img.alt = "";
      }
      document.body.classList.remove("is-lightbox");
    }

    function openBox(src, alt) {
      if (!src || !img) return;
      img.src = src;
      img.alt = alt || "";
      box.hidden = false;
      document.body.classList.add("is-lightbox");
      if (closeBtn) closeBtn.focus();
    }

    document.addEventListener("click", function (event) {
      if (box.hidden) {
        const openBtn = event.target.closest(".visit:not(.visit--own) .visit__gallery-open, .visit:not(.visit--own) .visit__gallery-item");
        if (!openBtn) return;
        const photo = openBtn.querySelector("img") || (openBtn.tagName === "IMG" ? openBtn : null);
        if (!photo || !photo.src) return;
        event.preventDefault();
        event.stopPropagation();
        openBox(photo.currentSrc || photo.src, photo.alt);
        return;
      }
      if (event.target === box || event.target.closest("[data-lightbox-close]")) {
        event.preventDefault();
        closeBox();
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !box.hidden) {
        event.preventDefault();
        closeBox();
      }
    });
  }

  function bindModal() {
    const modal = document.getElementById("profile-modal");
    const body = modal && modal.querySelector("[data-profile-modal-body]");
    if (!modal || !body) return;
    let lastFocus = null;

    function close() {
      const box = document.getElementById("photo-lightbox");
      if (box && !box.hidden) return;
      modal.hidden = true;
      document.body.classList.remove("is-profile-modal");
      body.innerHTML = "";
      if (lastFocus && typeof lastFocus.focus === "function") lastFocus.focus();
    }

    function open() {
      modal.hidden = false;
      document.body.classList.add("is-profile-modal");
    }

    function profileIdFrom(el) {
      return (
        el.getAttribute("data-profile-modal") ||
        (el.getAttribute("href") || "").match(/\/explorer\/profil\/([0-9a-f-]+)/i)?.[1] ||
        ""
      );
    }

    function load(id, tab) {
      if (!id) return;
      open();
      body.innerHTML = '<p class="profile-modal__loading">Ouverture du profil…</p>';
      fetch("/explorer/profil/" + id + "/", {
        credentials: "same-origin",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "HX-Request": "true",
          Accept: "text/html",
        },
      })
        .then(function (res) {
          if (!res.ok) throw new Error("Profil introuvable.");
          return res.text();
        })
        .then(function (html) {
          body.innerHTML = html;
          const title = body.querySelector(".visit__name");
          if (title) title.id = "profile-modal-title";
          bindVisitTabs(body);
          if (tab) activateTab(body, tab);
          const closeBtn = body.querySelector("[data-profile-modal-close]");
          if (closeBtn && !tab) closeBtn.focus();
        })
        .catch(function () {
          body.innerHTML =
            '<p class="profile-modal__loading">Impossible d’ouvrir ce profil. Réessayez.</p>';
        });
    }

    document.addEventListener("click", function (event) {
      if (event.target.closest("[data-profile-modal-close]")) {
        event.preventDefault();
        close();
        return;
      }
      if (document.body.classList.contains("is-guest")) return;
      if (
        event.target.closest(
          "[data-msg-open], [data-msg-like-required], [data-swipe], [data-likes-pass], [data-likes-super], [data-likes-back], .history__actions, .likes__card-actions, .likes__card-bar"
        )
      ) {
        return;
      }
      const trigger = event.target.closest("[data-profile-modal], a[href*='/explorer/profil/']");
      if (!trigger) return;
      if (event.target.closest("[data-photo-step]")) return;
      const id = profileIdFrom(trigger);
      if (!id) return;
      event.preventDefault();
      lastFocus = trigger;
      load(id, trigger.getAttribute("data-profile-tab") || "");
    });

    document.addEventListener("keydown", function (event) {
      if (event.key !== "Enter" && event.key !== " ") return;
      const trigger = event.target.closest("[data-profile-modal]");
      if (!trigger || document.body.classList.contains("is-guest")) return;
      if (event.target.closest("[data-photo-step]")) return;
      event.preventDefault();
      lastFocus = trigger;
      load(profileIdFrom(trigger), trigger.getAttribute("data-profile-tab") || "");
    });

    document.addEventListener("keydown", function (event) {
      if (event.key !== "Escape") return;
      const box = document.getElementById("photo-lightbox");
      if (box && !box.hidden) return;
      if (!modal.hidden) close();
    });

    const params = new URLSearchParams(window.location.search);
    const fromQuery = params.get("profil");
    if (fromQuery && !document.body.classList.contains("is-guest")) {
      load(fromQuery);
    }
  }

  function bindUnreadBadge() {
    if (window.timaloveRealtime) return;
    const tab = document.querySelector("[data-dock-messages]");
    const badge = document.querySelector("[data-unread-messages]");
    if (!tab || !badge || document.body.classList.contains("is-guest")) return;

    function render(count) {
      const n = Math.max(0, parseInt(count, 10) || 0);
      badge.hidden = n < 1;
      badge.textContent = n > 99 ? "99+" : String(n);
      if (n > 0) {
        tab.setAttribute("aria-label", "Messages, " + n + (n > 1 ? " non lus" : " non lu"));
      } else if (tab.getAttribute("aria-current") === "page") {
        tab.setAttribute("aria-label", "Messages");
      } else {
        tab.removeAttribute("aria-label");
      }
    }

    window.timaloveRenderUnreadBadge = render;

    function refresh() {
      fetch("/api/messages/unread-count/", {
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then(function (res) {
          if (!res.ok) throw new Error("unread");
          return res.json();
        })
        .then(function (data) {
          render(data && data.count);
        })
        .catch(function () {});
    }

    const onThreadPage = document.body.classList.contains("messages-page");
    const onInboxPage = document.body.classList.contains("messages-inbox-page");
    window.timaloveRefreshUnreadBadge = refresh;
    refresh();
    let pollMs = 0;
    if (onInboxPage) pollMs = 5000;
    else if (!onThreadPage) pollMs = 20000;
    if (pollMs > 0) {
      window.setInterval(refresh, pollMs);
    }
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) refresh();
    });
    window.addEventListener("focus", refresh);
  }

  bindMenu();
  bindLightbox();
  bindModal();
  bindUnreadBadge();
})();
