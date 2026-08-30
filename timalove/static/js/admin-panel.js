(function () {
  document.addEventListener("DOMContentLoaded", () => {
    const shell = document.querySelector("[data-admin-shell]");
    if (!shell) return;
    const sidebar = shell.querySelector("[data-admin-sidebar]");
    const backdrop = shell.querySelector("[data-admin-nav-close]");
    const openBtn = shell.querySelector("[data-admin-nav-open]");

    function openNav() {
      shell.classList.add("is-nav-open");
      if (backdrop) backdrop.hidden = false;
    }
    function closeNav() {
      shell.classList.remove("is-nav-open");
      if (backdrop) backdrop.hidden = true;
    }

    function closeSheets() {
      document.querySelectorAll("[data-mon-sheet]").forEach((el) => {
        el.hidden = true;
      });
      document.body.classList.remove("is-adm-sheet");
    }

    function openSheet(id) {
      if (!id) return;
      document.querySelectorAll("[data-mon-sheet]").forEach((el) => {
        el.hidden = el.id !== id;
      });
      document.body.classList.add("is-adm-sheet");
    }

    openBtn?.addEventListener("click", openNav);
    backdrop?.addEventListener("click", closeNav);
    sidebar?.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        if (window.matchMedia("(max-width: 1023px)").matches) closeNav();
      });
    });
    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      const openSheetEl = document.querySelector("[data-mon-sheet]:not([hidden])");
      if (openSheetEl) {
        closeSheets();
        return;
      }
      closeNav();
    });

    document.querySelectorAll("[data-mon-open]").forEach((btn) => {
      btn.addEventListener("click", () => openSheet(btn.getAttribute("data-mon-open")));
    });
    document.querySelectorAll("[data-mon-close]").forEach((btn) => {
      btn.addEventListener("click", closeSheets);
    });
    if (document.querySelector("[data-mon-sheet]:not([hidden])")) {
      document.body.classList.add("is-adm-sheet");
    }

    document.querySelectorAll("[data-promo-uses]").forEach((wrap) => {
      const unlimited = wrap.querySelector("[data-promo-unlimited]");
      const field = wrap.querySelector("[data-promo-max-field]");
      const input = wrap.querySelector("[data-promo-max-input]");
      function syncPromoUses() {
        const isUnlimited = Boolean(unlimited?.checked);
        if (field) field.hidden = isUnlimited;
        if (input) {
          input.disabled = isUnlimited;
          input.required = !isUnlimited;
        }
      }
      unlimited?.addEventListener("change", syncPromoUses);
      syncPromoUses();
    });

    document.querySelectorAll("[data-features-autosave]").forEach((form) => {
      const status = form.querySelector("[data-features-status]");
      form.addEventListener("change", async (event) => {
        const input = event.target;
        if (!(input instanceof HTMLInputElement) || input.type !== "checkbox") return;
        const body = new FormData(form);
        try {
          const res = await fetch(window.location.href, {
            method: "POST",
            body,
            credentials: "same-origin",
            headers: { "X-Requested-With": "XMLHttpRequest" },
          });
          const data = await res.json().catch(() => ({}));
          if (status) {
            status.hidden = false;
            status.textContent = data.ok
              ? "Appliqué immédiatement sur le site."
              : data.error || "Enregistrement impossible.";
            status.classList.toggle("is-error", !data.ok);
          }
        } catch {
          if (status) {
            status.hidden = false;
            status.textContent = "Enregistrement impossible.";
            status.classList.add("is-error");
          }
        }
      });
    });

    const campaignForm = document.querySelector("[data-campaign-form]");
    if (campaignForm) {
      const sendMode = campaignForm.querySelector("[data-campaign-send-mode]");
      const scheduledWrap = campaignForm.querySelector("[data-campaign-scheduled-wrap]");
      const scheduledInput = campaignForm.querySelector("#crm-scheduled");
      const titleInput = campaignForm.querySelector("[data-campaign-title]");
      const bodyInput = campaignForm.querySelector("[data-campaign-body]");
      const imageInput = campaignForm.querySelector("[data-campaign-image]");
      const imagePreview = campaignForm.querySelector("[data-campaign-image-preview]");
      const imageImg = campaignForm.querySelector("[data-campaign-image-img]");
      const imageClear = campaignForm.querySelector("[data-campaign-image-clear]");
      const liveTitle = campaignForm.querySelector("[data-campaign-live-title]");
      const liveText = campaignForm.querySelector("[data-campaign-live-text]");
      const livePhoto = campaignForm.querySelector("[data-campaign-live-photo]");
      let previewUrl = "";

      function syncScheduled() {
        const scheduled = sendMode && sendMode.value === "scheduled";
        if (scheduledWrap) scheduledWrap.hidden = !scheduled;
        if (scheduledInput) scheduledInput.required = Boolean(scheduled);
      }

      function syncLiveCopy() {
        if (liveTitle) liveTitle.textContent = (titleInput?.value || "").trim() || "Titre de la campagne";
        if (liveText) liveText.textContent = (bodyInput?.value || "").trim() || "Votre message apparaîtra ici.";
      }

      function setLivePhoto(src) {
        if (!livePhoto) return;
        if (src) {
          livePhoto.innerHTML = '<img src="' + src + '" alt="">';
        } else {
          livePhoto.innerHTML = "<span>✉</span>";
        }
      }

      function clearImage() {
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        previewUrl = "";
        if (imageInput) imageInput.value = "";
        if (imagePreview) imagePreview.hidden = true;
        if (imageImg) imageImg.removeAttribute("src");
        setLivePhoto("");
      }

      sendMode?.addEventListener("change", syncScheduled);
      titleInput?.addEventListener("input", syncLiveCopy);
      bodyInput?.addEventListener("input", syncLiveCopy);
      imageInput?.addEventListener("change", () => {
        const file = imageInput.files && imageInput.files[0];
        if (!file) {
          clearImage();
          return;
        }
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        previewUrl = URL.createObjectURL(file);
        if (imageImg) imageImg.src = previewUrl;
        if (imagePreview) imagePreview.hidden = false;
        setLivePhoto(previewUrl);
      });
      imageClear?.addEventListener("click", clearImage);
      syncScheduled();
      syncLiveCopy();
    }

    document.querySelectorAll("[data-city-picker]").forEach((picker) => {
      const url = picker.getAttribute("data-cities-url");
      const hidden = picker.querySelector("[data-city-value]");
      const search = picker.querySelector("[data-city-search]");
      const list = picker.querySelector("[data-city-list]");
      const clearBtn = picker.querySelector("[data-city-clear]");
      if (!url || !hidden || !search || !list) return;

      let debounceTimer = 0;
      let fetchAbort = null;
      let activeIndex = -1;

      function escapeHtml(value) {
        return String(value)
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;");
      }

      function options() {
        return Array.from(list.querySelectorAll("[data-city-option]"));
      }

      function setOpen(open) {
        list.hidden = !open;
        search.setAttribute("aria-expanded", open ? "true" : "false");
        if (!open) activeIndex = -1;
        options().forEach((el) => el.classList.remove("is-active"));
      }

      function syncClearButton() {
        if (!clearBtn) return;
        clearBtn.hidden = !(hidden.value || search.value.trim());
      }

      function selectCity(name, label) {
        hidden.value = name || "";
        search.value = label || (name || "");
        options().forEach((el) => {
          el.classList.toggle("is-selected", (el.getAttribute("data-city-name") || "") === (name || ""));
        });
        syncClearButton();
        setOpen(false);
      }

      function renderCities(cities, query) {
        const q = (query || "").trim();
        let html = '<li class="adm-city-picker__option' + (hidden.value ? "" : " is-selected") + '" role="option" data-city-option data-city-name="">Toutes les villes</li>';
        if (cities.length) {
          cities.forEach((city) => {
            const selected = hidden.value === city.name ? " is-selected" : "";
            html +=
              '<li class="adm-city-picker__option' +
              selected +
              '" role="option" data-city-option data-city-name="' +
              escapeHtml(city.name) +
              '" data-city-count="' +
              city.count +
              '"><span class="adm-city-picker__name">' +
              escapeHtml(city.name) +
              '</span><span class="adm-city-picker__count">' +
              city.count +
              " membre" +
              (city.count > 1 ? "s" : "") +
              "</span></li>";
          });
        } else if (q) {
          html += '<li class="adm-city-picker__empty">Aucune ville trouvée pour « ' + escapeHtml(q) + " ».</li>";
        }
        list.innerHTML = html;
        activeIndex = -1;
      }

      function loadCities(query) {
        const q = (query || "").trim();
        if (fetchAbort) fetchAbort.abort();
        fetchAbort = new AbortController();
        const params = q ? "?q=" + encodeURIComponent(q) : "";
        fetch(url + params, {
          credentials: "same-origin",
          headers: { "X-Requested-With": "XMLHttpRequest" },
          signal: fetchAbort.signal,
        })
          .then((res) => res.json())
          .then((data) => {
            if (!data.ok) return;
            renderCities(data.cities || [], q);
            setOpen(true);
          })
          .catch((err) => {
            if (err.name === "AbortError") return;
          });
      }

      function scheduleSearch() {
        window.clearTimeout(debounceTimer);
        debounceTimer = window.setTimeout(() => {
          loadCities(search.value);
        }, 180);
      }

      search.addEventListener("blur", () => {
        window.setTimeout(() => {
          if (!list.hidden) return;
          const typed = search.value.trim();
          if (!typed) {
            selectCity("", "");
            return;
          }
          const match = options().find((el) => (el.getAttribute("data-city-name") || "") === typed);
          if (match) {
            selectCity(typed, typed);
          } else if (hidden.value) {
            search.value = hidden.value;
          } else {
            search.value = "";
          }
          syncClearButton();
        }, 160);
      });

      search.addEventListener("focus", () => {
        loadCities(search.value);
      });

      search.addEventListener("input", () => {
        hidden.value = "";
        options().forEach((el) => el.classList.remove("is-selected"));
        syncClearButton();
        scheduleSearch();
      });

      search.addEventListener("keydown", (event) => {
        const items = options();
        if (event.key === "ArrowDown") {
          event.preventDefault();
          if (list.hidden) loadCities(search.value);
          activeIndex = Math.min(activeIndex + 1, items.length - 1);
          items.forEach((el, idx) => el.classList.toggle("is-active", idx === activeIndex));
          items[activeIndex]?.scrollIntoView({ block: "nearest" });
          return;
        }
        if (event.key === "ArrowUp") {
          event.preventDefault();
          activeIndex = Math.max(activeIndex - 1, 0);
          items.forEach((el, idx) => el.classList.toggle("is-active", idx === activeIndex));
          items[activeIndex]?.scrollIntoView({ block: "nearest" });
          return;
        }
        if (event.key === "Enter") {
          if (activeIndex >= 0 && items[activeIndex]) {
            event.preventDefault();
            items[activeIndex].click();
          }
          return;
        }
        if (event.key === "Escape") {
          setOpen(false);
        }
      });

      list.addEventListener("click", (event) => {
        const option = event.target.closest("[data-city-option]");
        if (!option) return;
        const name = option.getAttribute("data-city-name") || "";
        const label = name || "Toutes les villes";
        selectCity(name, name ? name : "");
        if (!name) search.value = "";
      });

      clearBtn?.addEventListener("click", () => {
        selectCity("", "");
        search.value = "";
        search.focus();
        loadCities("");
      });

      document.addEventListener("click", (event) => {
        if (!picker.contains(event.target)) setOpen(false);
      });

      syncClearButton();
    });
  });
})();
