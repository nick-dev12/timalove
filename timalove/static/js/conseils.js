(function () {
  const modal = document.getElementById("conseil-detail-modal");
  if (!modal) return;

  const backdrop = modal.querySelector("[data-conseil-detail-dismiss]");
  const closeBtn = modal.querySelector("[data-conseil-detail-close]");
  const img = modal.querySelector("[data-conseil-detail-img]");
  const titleEl = modal.querySelector("[data-conseil-detail-title]");
  const introEl = modal.querySelector("[data-conseil-detail-intro]");
  const listEl = modal.querySelector("[data-conseil-detail-list]");
  const ctaWrap = modal.querySelector("[data-conseil-detail-cta]");
  const ctaLink = modal.querySelector("[data-conseil-detail-cta-link]");

  let lastFocus = null;

  function openDetail(payload) {
    if (!payload) return;
    lastFocus = document.activeElement;
    if (img) {
      img.src = payload.image || "";
      img.alt = payload.title ? `Illustration — ${payload.title}` : "";
    }
    if (titleEl) titleEl.textContent = payload.title || "";
    if (introEl) introEl.textContent = payload.detail?.intro || "";
    if (listEl) {
      listEl.innerHTML = "";
      (payload.detail?.bullets || []).forEach((line) => {
        const li = document.createElement("li");
        li.textContent = line;
        listEl.appendChild(li);
      });
    }
    const label = payload.detail?.cta_label;
    const href = payload.detail?.cta_href;
    if (ctaWrap && ctaLink) {
      if (label && href) {
        ctaLink.textContent = label;
        ctaLink.href = href;
        ctaWrap.hidden = false;
      } else {
        ctaWrap.hidden = true;
      }
    }
    modal.hidden = false;
    document.body.classList.add("conseil-detail-open");
    titleEl?.focus();
  }

  function closeDetail() {
    modal.hidden = true;
    document.body.classList.remove("conseil-detail-open");
    if (lastFocus && typeof lastFocus.focus === "function") lastFocus.focus();
  }

  document.querySelectorAll("[data-conseil-open]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const raw = btn.getAttribute("data-conseil-payload");
      if (!raw) return;
      try {
        openDetail(JSON.parse(raw));
      } catch (_) {
        /* ignore */
      }
    });
  });

  backdrop?.addEventListener("click", closeDetail);
  closeBtn?.addEventListener("click", closeDetail);
  modal.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") closeDetail();
  });

  const hash = window.location.hash.replace(/^#/, "");
  if (hash) {
    const trigger = document.querySelector(`[data-conseil-open][data-conseil-id="${hash}"]`);
    trigger?.click();
  }
})();
