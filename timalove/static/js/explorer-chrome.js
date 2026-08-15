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
      const photos = event.target.closest("[data-photos][data-profile-modal]");
      if (!photos || document.body.classList.contains("is-guest")) return;
      event.preventDefault();
      photos.click();
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

  bindMenu();
  bindLightbox();
  bindModal();
})();
