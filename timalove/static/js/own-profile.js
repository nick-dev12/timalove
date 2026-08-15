/**
 * TimaLove — Mon profil : enregistrement par bloc.
 */
(function () {
  function cookie(name) {
    const m = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return m ? decodeURIComponent(m[1]) : "";
  }

  function csrf() {
    return cookie("csrftoken");
  }

  const ICONS = {
    plane: '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" d="M2 12l20-8-8 20-3-7-7-3z"/></svg>',
    book: '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="none" stroke="currentColor" stroke-width="1.7" d="M4 5h7a3 3 0 0 1 3 3v13H7a3 3 0 0 0-3 3V5zm9 0h7v16h-7"/></svg>',
    music: '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="none" stroke="currentColor" stroke-width="1.7" d="M9 18V6l12-2v12"/><circle cx="7" cy="18" r="2.4" fill="none" stroke="currentColor" stroke-width="1.7"/><circle cx="19" cy="16" r="2.4" fill="none" stroke="currentColor" stroke-width="1.7"/></svg>',
    camera: '<svg viewBox="0 0 24 24" width="16" height="16"><rect x="3" y="7" width="18" height="13" rx="2" fill="none" stroke="currentColor" stroke-width="1.7"/><circle cx="12" cy="13.5" r="3.2" fill="none" stroke="currentColor" stroke-width="1.7"/></svg>',
    dumbbell: '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" d="M6 9v6M9 8v8M15 8v8M18 9v6M6 12h12"/></svg>',
    palette: '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="none" stroke="currentColor" stroke-width="1.7" d="M12 3a9 9 0 1 0 0 18h1.5A2.5 2.5 0 0 0 16 18.5V18a2 2 0 0 1 2-2h.5A3.5 3.5 0 0 0 22 12.5 9 9 0 0 0 12 3z"/></svg>',
    coffee: '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="none" stroke="currentColor" stroke-width="1.7" d="M5 9h11v6a4 4 0 0 1-4 4H9a4 4 0 0 1-4-4V9zm11 1h2.5A2.5 2.5 0 0 1 21 12.5 2.5 2.5 0 0 1 18.5 15H16"/></svg>',
    film: '<svg viewBox="0 0 24 24" width="16" height="16"><rect x="3" y="5" width="18" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="1.7"/><path fill="none" stroke="currentColor" stroke-width="1.7" d="M7 5v14M17 5v14"/></svg>',
    chef: '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="none" stroke="currentColor" stroke-width="1.7" d="M8 11c-2 0-3-1.6-3-3.2C5 6 7 5 8.5 6c.4-2 4.6-2 5 0C15 5 17 6 17 7.8c0 1.6-1 3.2-3 3.2H8zm0 0v9h8v-9"/></svg>',
    game: '<svg viewBox="0 0 24 24" width="16" height="16"><rect x="2" y="8" width="20" height="10" rx="5" fill="none" stroke="currentColor" stroke-width="1.7"/><path fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" d="M8 13h4M10 11v4"/></svg>',
    leaf: '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="none" stroke="currentColor" stroke-width="1.7" d="M5 19C5 10 10 4 20 4 20 14 14 19 5 19z"/></svg>',
    heart: '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="none" stroke="currentColor" stroke-width="1.7" d="M12 20.5C4.5 14.2 1.5 9.8 1.5 5.8 1.5 2.8 3.8 1 6.6 1c2.1 0 4 1.1 5.4 2.9C13.4 2.1 15.3 1 17.4 1c2.8 0 5.1 1.8 5.1 4.8 0 4-3 8.4-10.5 14.7z"/></svg>',
    ring: '<svg viewBox="0 0 24 24" width="16" height="16"><circle cx="12" cy="13" r="6" fill="none" stroke="currentColor" stroke-width="1.7"/><path fill="none" stroke="currentColor" stroke-width="1.7" d="M9 8.2 12 4l3 4.2"/></svg>',
    spark: '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" d="M12 3v4M12 17v4M3 12h4M17 12h4M6.2 6.2l2.8 2.8M15 15l2.8 2.8M17.8 6.2 15 9M9 15l-2.8 2.8"/></svg>',
    mountain: '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" d="M3 19h18L14 7l-3 5-2-3z"/></svg>',
    rose: '<svg viewBox="0 0 24 24" width="16" height="16"><circle cx="12" cy="9" r="4" fill="none" stroke="currentColor" stroke-width="1.7"/><path fill="none" stroke="currentColor" stroke-width="1.7" d="M12 13v8M9 18c2-1 4-1 6 0"/></svg>',
    wave: '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="none" stroke="currentColor" stroke-width="1.7" d="M3 14c2 2 4 2 6 0s4-2 6 0 4 2 6 0"/></svg>',
    gift: '<svg viewBox="0 0 24 24" width="16" height="16"><rect x="4" y="10" width="16" height="10" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.7"/><path fill="none" stroke="currentColor" stroke-width="1.7" d="M12 10v10M4 14h16M8 10c0-2 1.5-4 4-4s4 2 4 4"/></svg>',
    smile: '<svg viewBox="0 0 24 24" width="16" height="16"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.7"/><path fill="none" stroke="currentColor" stroke-width="1.7" d="M8 14c1.2 2 6.8 2 8 0M9 10h.1M15 10h.1"/></svg>',
  };

  document.addEventListener("DOMContentLoaded", () => {
    const root = document.querySelector("[data-own-profile]");
    if (!root) return;

    root.querySelectorAll("[data-icon]").forEach((el) => {
      el.innerHTML = ICONS[el.dataset.icon] || "";
    });

    const maxPhotos = Number(root.dataset.maxPhotos || 5);
    const tabs = [...root.querySelectorAll(".visit__tab")];
    const panels = {
      about: document.getElementById("panel-about"),
      gallery: document.getElementById("panel-gallery"),
      filters: document.getElementById("panel-filters"),
      settings: document.getElementById("panel-settings"),
    };

    function setMsg(key, text, isError) {
      const el = root.querySelector('[data-save-msg="' + key + '"]');
      if (!el) return;
      el.hidden = !text;
      el.textContent = text || "";
      el.classList.toggle("is-error", Boolean(isError));
    }

    function showTab(key) {
      if (!panels[key]) key = "about";
      tabs.forEach((tab) => {
        const on = tab.getAttribute("data-tab") === key;
        tab.classList.toggle("is-active", on);
        tab.setAttribute("aria-selected", on ? "true" : "false");
      });
      Object.keys(panels).forEach((k) => {
        if (panels[k]) panels[k].hidden = k !== key;
      });
      const url = new URL(window.location.href);
      if (key === "about") url.searchParams.delete("tab");
      else url.searchParams.set("tab", key);
      history.replaceState({}, "", url);
    }

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => showTab(tab.getAttribute("data-tab")));
    });
    const initialTab = new URLSearchParams(window.location.search).get("tab");
    if (initialTab && panels[initialTab]) showTab(initialTab);

    async function postJSON(url, body) {
      const res = await fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.message || "Erreur");
      return data;
    }

    async function postFile(url, file, kind) {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("kind", kind);
      const res = await fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-CSRFToken": csrf() },
        body: fd,
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.message || "Upload impossible");
      return data;
    }

    root.querySelectorAll("[data-interest], [data-trait]").forEach((btn) => {
      btn.addEventListener("click", () => btn.classList.toggle("is-on"));
    });

    function selected(selector, attr) {
      return [...root.querySelectorAll(selector)]
        .filter((b) => b.classList.contains("is-on"))
        .map((b) => b.getAttribute(attr));
    }

    const profileForm = root.querySelector("[data-profile-form]");
    const filtersForm = root.querySelector("[data-filters-form]");

    async function withButton(btn, key, work, okText) {
      btn.disabled = true;
      setMsg(key, "", false);
      try {
        await work();
        setMsg(key, okText, false);
      } catch (err) {
        setMsg(key, err.message, true);
      } finally {
        btn.disabled = false;
      }
    }

    async function saveIdentity() {
      if (!profileForm) return;
      if (!profileForm.reportValidity()) throw new Error("Complétez les champs obligatoires.");
      const fd = new FormData(profileForm);
      await postJSON("/api/profile/update/", {
        first_name: fd.get("first_name"),
        last_name: fd.get("last_name"),
        age: fd.get("age"),
        gender: fd.get("gender"),
        profession: fd.get("profession"),
        city: fd.get("city"),
        commune: fd.get("commune"),
        country: fd.get("country"),
        residence_country: fd.get("residence_country"),
        religion: fd.get("religion"),
        relationship_intent: fd.get("relationship_intent"),
        life_project: fd.get("life_project"),
        phone: fd.get("phone"),
        bio: fd.get("bio"),
        looking_for: fd.get("looking_for"),
      });
      const name = fd.get("first_name") || "";
      const age = fd.get("age");
      root.querySelector("[data-display-name]").textContent = name;
      const ageEl = root.querySelector("[data-display-age]");
      const hideAge = root.querySelector('[data-privacy-form] [name="hide_age"]');
      if (ageEl) ageEl.textContent = (hideAge && hideAge.checked) || !age ? "" : ", " + age;
      const loc = [fd.get("commune") || "", fd.get("city") || "", fd.get("country") || ""].filter(Boolean).join(", ");
      const locEl = root.querySelector("[data-display-location]");
      if (locEl) locEl.textContent = loc || "TimaLove";
      const roleEl = root.querySelector("[data-display-role]");
      if (roleEl) roleEl.textContent = fd.get("profession") || "";
    }

    async function saveInterests() {
      await postJSON("/api/profile/update/", {
        interests: selected("[data-interest]", "data-interest"),
        personality_traits: selected("[data-trait]", "data-trait"),
      });
    }

    const valueInput = root.querySelector("[data-value-input]");
    const valueList = root.querySelector("[data-value-list]");
    const MAX_VALUES = 12;

    function currentValues() {
      return [...root.querySelectorAll("[data-value-chip]")]
        .map((el) => (el.dataset.valueChip || "").trim())
        .filter(Boolean);
    }

    function addValueChip(label) {
      if (!valueList) return;
      const chip = document.createElement("span");
      chip.className = "visit-values__chip";
      chip.dataset.valueChip = label;
      chip.appendChild(document.createTextNode(label + " "));
      const btn = document.createElement("button");
      btn.type = "button";
      btn.setAttribute("data-value-remove", "");
      btn.setAttribute("aria-label", "Retirer");
      btn.textContent = "×";
      chip.appendChild(btn);
      valueList.appendChild(chip);
    }

    function tryAddValue() {
      const label = (valueInput?.value || "").trim().slice(0, 40);
      if (!label) return;
      const existing = currentValues().map((v) => v.toLowerCase());
      if (existing.includes(label.toLowerCase())) {
        valueInput.value = "";
        return;
      }
      if (existing.length >= MAX_VALUES) {
        setMsg("values", "Vous pouvez ajouter jusqu’à " + MAX_VALUES + " valeurs.", true);
        return;
      }
      addValueChip(label);
      valueInput.value = "";
      setMsg("values", "", false);
    }

    root.querySelector("[data-value-add]")?.addEventListener("click", tryAddValue);
    valueInput?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        tryAddValue();
      }
    });
    valueList?.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-value-remove]");
      if (!btn) return;
      btn.closest("[data-value-chip]")?.remove();
    });

    async function saveValues() {
      await postJSON("/api/profile/update/", {
        life_values: currentValues(),
      });
    }

    async function saveFilters() {
      if (!filtersForm) return;
      const fd = new FormData(filtersForm);
      await postJSON("/api/profile/filters/", {
        age_min: fd.get("age_min"),
        age_max: fd.get("age_max"),
        gender: fd.get("gender"),
        religion: fd.get("religion"),
        country: fd.get("country"),
        verified_only: fd.get("verified_only") === "on",
        online_only: fd.get("online_only") === "on",
      });
    }

    async function savePrivacy() {
      const form = root.querySelector("[data-privacy-form]");
      if (!form) return;
      const fd = new FormData(form);
      await postJSON("/api/profile/update/", {
        hide_age: fd.get("hide_age") === "on",
        is_hidden: fd.get("is_hidden") === "on",
        last_seen_visibility: fd.get("last_seen_visibility"),
      });
      const ageEl = root.querySelector("[data-display-age]");
      const age = profileForm?.querySelector('[name="age"]')?.value;
      if (ageEl) ageEl.textContent = fd.get("hide_age") === "on" || !age ? "" : ", " + age;
    }

    async function saveNotifications() {
      const form = root.querySelector("[data-notifs-form]");
      if (!form) return;
      const fd = new FormData(form);
      await postJSON("/api/profile/update/", {
        notification_preferences: {
          push: fd.get("push") === "on",
          likes: fd.get("likes") === "on",
          matches: fd.get("matches") === "on",
          messages: fd.get("messages") === "on",
        },
      });
    }

    root.querySelector('[data-save="identity"]')?.addEventListener("click", (e) => {
      void withButton(e.currentTarget, "identity", saveIdentity, "Profil enregistré.");
    });
    root.querySelector('[data-save="interests"]')?.addEventListener("click", (e) => {
      void withButton(e.currentTarget, "interests", saveInterests, "Intérêts enregistrés.");
    });
    root.querySelector('[data-save="values"]')?.addEventListener("click", (e) => {
      void withButton(e.currentTarget, "values", saveValues, "Valeurs enregistrées.");
    });
    root.querySelector('[data-save="filters"]')?.addEventListener("click", (e) => {
      void withButton(e.currentTarget, "filters", saveFilters, "Filtres enregistrés.");
    });
    root.querySelector('[data-save="privacy"]')?.addEventListener("click", (e) => {
      void withButton(e.currentTarget, "privacy", savePrivacy, "Confidentialité enregistrée.");
    });
    root.querySelector('[data-save="notifications"]')?.addEventListener("click", (e) => {
      void withButton(e.currentTarget, "notifications", saveNotifications, "Notifications enregistrées.");
    });

    root.querySelectorAll("[data-checkout]").forEach((btn) => {
      btn.addEventListener("click", () => {
        void withButton(btn, "subscription", async () => {
          const data = await postJSON("/api/payments/checkout/", { tier: btn.getAttribute("data-checkout") });
          if (data.checkout_url) window.location.href = data.checkout_url;
        }, "Redirection vers le paiement…");
      });
    });

    root.querySelector("[data-boost]")?.addEventListener("click", (e) => {
      void withButton(e.currentTarget, "subscription", async () => {
        const data = await postJSON("/api/payments/checkout/", { kind: "boost" });
        if (data.checkout_url) window.location.href = data.checkout_url;
      }, "Redirection vers le paiement…");
    });

    root.querySelector("[data-delete-account]")?.addEventListener("click", (e) => {
      if (!window.confirm("Supprimer définitivement votre compte ? Cette action est irréversible.")) return;
      void withButton(e.currentTarget, "danger", async () => {
        const data = await postJSON("/api/profile/delete/", {});
        window.location.href = data.redirect || "/";
      }, "Compte supprimé.");
    });

    const gallery = root.querySelector("[data-gallery]");
    const galleryFile = root.querySelector("[data-gallery-file]");
    const avatarFile = root.querySelector("[data-avatar-file]");
    const heroImg = root.querySelector("[data-hero-img]");

    function photoCount() {
      return gallery ? gallery.querySelectorAll("[data-photo-id]").length : 0;
    }

    function syncAddButton() {
      const add = root.querySelector("[data-gallery-add]");
      if (!add) return;
      add.hidden = photoCount() >= maxPhotos;
    }

    function bindPhoto(item) {
      item.querySelector("[data-delete-photo]")?.addEventListener("click", async () => {
        try {
          await postJSON("/api/profile/photo/delete/", { id: item.dataset.photoId });
          item.remove();
          syncAddButton();
          setMsg("gallery", "Photo retirée.", false);
        } catch (err) {
          setMsg("gallery", err.message, true);
        }
      });
      item.querySelector("[data-set-primary]")?.addEventListener("click", async () => {
        try {
          const data = await postJSON("/api/profile/photo/primary/", { id: item.dataset.photoId });
          if (heroImg && data.url) {
            heroImg.src = data.url;
            heroImg.hidden = false;
          }
          window.location.reload();
        } catch (err) {
          setMsg("gallery", err.message, true);
        }
      });
    }

    gallery?.querySelectorAll("[data-photo-id]").forEach(bindPhoto);
    syncAddButton();

    function appendPhoto(photo) {
      if (!gallery) return;
      const fig = document.createElement("figure");
      fig.className = "visit__gallery-item" + (photo.is_primary ? " is-primary" : "");
      fig.dataset.photoId = photo.id;
      fig.innerHTML =
        '<div class="visit__gallery-frame"><img src="' +
        photo.url +
        '" alt="Nouvelle photo">' +
        (photo.is_primary
          ? '<span class="visit__gallery-flag">Profil</span>'
          : '<button type="button" class="visit__gallery-primary" data-set-primary>Photo de profil</button>') +
        '<button type="button" class="visit__gallery-remove" data-delete-photo>Retirer</button></div>';
      gallery.appendChild(fig);
      bindPhoto(fig);
      syncAddButton();
    }

    root.querySelector("[data-gallery-add]")?.addEventListener("click", () => galleryFile?.click());
    galleryFile?.addEventListener("change", async () => {
      const files = [...(galleryFile.files || [])];
      galleryFile.value = "";
      for (const file of files) {
        if (photoCount() >= maxPhotos) {
          setMsg("gallery", "Limite de " + maxPhotos + " photos atteinte.", true);
          break;
        }
        try {
          const data = await postFile("/api/profile/photo/", file, "gallery");
          appendPhoto(data);
          if (heroImg && data.is_primary) {
            heroImg.src = data.url;
            heroImg.hidden = false;
          }
          setMsg("gallery", "Photo ajoutée.", false);
        } catch (err) {
          setMsg("gallery", err.message, true);
        }
      }
    });

    function syncHeroChrome(hasPhoto) {
      const flag = root.querySelector("[data-hero-flag]");
      const del = root.querySelector("[data-hero-delete]");
      if (flag) flag.hidden = !hasPhoto;
      if (del) del.hidden = !hasPhoto;
    }

    root.querySelector("[data-hero-delete]")?.addEventListener("click", async () => {
      try {
        await postJSON("/api/profile/photo/delete/", { id: "primary" });
        window.location.reload();
      } catch (err) {
        setMsg("photo", err.message, true);
      }
    });

    root.querySelector("[data-avatar-pick]")?.addEventListener("click", () => avatarFile?.click());
    avatarFile?.addEventListener("change", async () => {
      const file = avatarFile.files?.[0];
      avatarFile.value = "";
      if (!file) return;
      try {
        const data = await postFile("/api/profile/photo/", file, "avatar");
        if (heroImg) {
          heroImg.src = data.url;
          heroImg.hidden = false;
        }
        const fallback = root.querySelector("[data-hero-fallback]");
        if (fallback) fallback.hidden = true;
        syncHeroChrome(true);
        setMsg("photo", "Photo mise à jour.", false);
      } catch (err) {
        setMsg("photo", err.message, true);
      }
    });
  });
})();
