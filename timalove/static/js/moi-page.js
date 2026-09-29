/**
 * Page Moi — menu CDC + tiroirs, modal photos plein écran.
 */
(function () {
  const photosModal = () => document.getElementById("moi-photos-modal");
  const photoView = () => document.getElementById("moi-photo-view");

  function mountPanels(root) {
    document.querySelectorAll("[data-moi-drawer]").forEach((drawer) => {
      const key = drawer.getAttribute("data-moi-drawer");
      if (!key || key === "photos") return;
      const panel = root.querySelector('[data-moi-panel="' + key + '"]');
      if (panel && !drawer.contains(panel)) {
        panel.hidden = false;
        panel.classList.add("is-mounted");
        drawer.appendChild(panel);
      }
      if (key === "security") {
        root.querySelectorAll("[data-moi-security-part]").forEach((part) => {
          if (!drawer.contains(part)) drawer.appendChild(part);
        });
      }
    });
    const photosPanel = root.querySelector('[data-moi-panel="photos"]');
    const mount = document.querySelector("[data-moi-photos-mount]");
    if (photosPanel && mount && !mount.contains(photosPanel)) {
      photosPanel.hidden = false;
      photosPanel.classList.add("is-mounted");
      mount.appendChild(photosPanel);
    }
  }

  function closeAllItems() {
    document.querySelectorAll("[data-moi-item]").forEach((item) => {
      item.classList.remove("is-open");
      const trigger = item.querySelector("[data-moi-open]");
      if (trigger) trigger.setAttribute("aria-expanded", "false");
      const drawer = item.querySelector("[data-moi-drawer]");
      if (drawer) drawer.hidden = true;
    });
  }

  function closePhotosModal() {
    const modal = photosModal();
    if (modal) modal.hidden = true;
    document.body.classList.remove("moi-photos-open");
    const trigger = document.querySelector('[data-moi-open="photos"]');
    trigger?.setAttribute("aria-expanded", "false");
    document.querySelector('[data-moi-item="photos"]')?.classList.remove("is-open");
    closePhotoView();
  }

  function openPhotosModal() {
    closeAllItems();
    const modal = photosModal();
    if (!modal) return;
    modal.hidden = false;
    document.body.classList.add("moi-photos-open");
    const item = document.querySelector('[data-moi-item="photos"]');
    const trigger = item?.querySelector("[data-moi-open]");
    item?.classList.add("is-open");
    trigger?.setAttribute("aria-expanded", "true");
    modal.querySelector("[data-moi-photos-close]")?.focus();
  }

  function closePhotoView() {
    const view = photoView();
    if (!view) return;
    view.hidden = true;
    document.body.classList.remove("moi-photo-view-open");
  }

  function openPhotoView(src, alt) {
    const view = photoView();
    const img = view?.querySelector("[data-moi-photo-view-img]");
    if (!view || !img || !src) return;
    img.src = src;
    img.alt = alt || "Photo";
    view.hidden = false;
    document.body.classList.add("moi-photo-view-open");
    view.querySelector("[data-moi-photo-view-close]")?.focus();
  }

  function openDrawer(key) {
    if (!key) return;
    if (key === "photos") {
      const modal = photosModal();
      if (modal && !modal.hidden) {
        closePhotosModal();
        return;
      }
      openPhotosModal();
      return;
    }
    closePhotosModal();
    const item = document.querySelector('[data-moi-item="' + key + '"]');
    const drawer = document.querySelector('[data-moi-drawer="' + key + '"]');
    if (!item || !drawer) return;

    const isOpen = item.classList.contains("is-open");
    closeAllItems();
    if (isOpen) return;

    item.classList.add("is-open");
    drawer.hidden = false;
    const trigger = item.querySelector("[data-moi-open]");
    trigger?.setAttribute("aria-expanded", "true");
    drawer.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  window.moiOpenDrawer = openDrawer;

  document.addEventListener("DOMContentLoaded", () => {
    if (!document.body.classList.contains("moi-page")) return;
    const root = document.querySelector("[data-own-profile]");
    if (!root) return;

    mountPanels(root);

    document.querySelectorAll("[data-moi-open]").forEach((btn) => {
      btn.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        openDrawer(btn.getAttribute("data-moi-open"));
        const menu = document.querySelector("[data-moi-quick-menu]");
        const menuBtn = document.querySelector("[data-moi-menu-toggle]");
        if (menu) menu.hidden = true;
        menuBtn?.setAttribute("aria-expanded", "false");
      });
    });

    document.querySelectorAll("[data-moi-photos-close]").forEach((el) => {
      el.addEventListener("click", closePhotosModal);
    });
    document.querySelectorAll("[data-moi-photo-view-close]").forEach((el) => {
      el.addEventListener("click", closePhotoView);
    });
    photoView()?.addEventListener("click", (event) => {
      if (event.target === photoView()) closePhotoView();
    });

    document.addEventListener("click", (event) => {
      if (event.target.closest("[data-delete-photo], [data-set-primary], [data-gallery-add]")) return;
      const frame = event.target.closest(".moi-photos-modal [data-photo-id]");
      if (!frame) return;
      const img = frame.querySelector("img");
      if (!img?.src) return;
      event.preventDefault();
      openPhotoView(img.src, img.alt);
    });

    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      if (photoView() && !photoView().hidden) {
        closePhotoView();
        return;
      }
      if (photosModal() && !photosModal().hidden) closePhotosModal();
    });

    const menuBtn = document.querySelector("[data-moi-menu-toggle]");
    const menu = document.querySelector("[data-moi-quick-menu]");
    menuBtn?.addEventListener("click", () => {
      const willOpen = Boolean(menu?.hidden);
      if (menu) menu.hidden = !willOpen;
      menuBtn.setAttribute("aria-expanded", willOpen ? "true" : "false");
    });
    document.addEventListener("click", (ev) => {
      if (!menu || menu.hidden) return;
      if (menu.contains(ev.target) || menuBtn?.contains(ev.target)) return;
      menu.hidden = true;
      menuBtn?.setAttribute("aria-expanded", "false");
    });

    const params = new URLSearchParams(window.location.search);
    const tab = params.get("tab");
    const map = { about: "mariage", filters: "preferences", gallery: "photos", settings: "edit" };
    const fromTab = map[tab];
    const hash = window.location.hash.replace(/^#/, "");
    if (hash === "bloques") {
      openDrawer("security");
    } else if (hash === "projet-mariage") {
      openDrawer("mariage");
    } else if (params.get("section") === "notifications") {
      openDrawer("notifications");
    } else if (fromTab) {
      openDrawer(fromTab);
    }
  });
})();
