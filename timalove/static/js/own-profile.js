/**
 * TimaLove — Mon profil : enregistrement par bloc.
 */
(function () {
  function cookie(name) {
    const m = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return m ? decodeURIComponent(m[1]) : "";
  }

  function csrf() {
    return cookie("csrftoken") || document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
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
      if (text) el.scrollIntoView({ behavior: "smooth", block: "nearest" });
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
      if (key === "about") {
        url.searchParams.delete("tab");
        url.searchParams.delete("section");
      } else {
        url.searchParams.set("tab", key);
        if (key !== "settings") url.searchParams.delete("section");
      }
      history.replaceState({}, "", url);
      if (key === "settings") {
        const section = getSettingsSectionFromUrl();
        if (MODAL_SECTIONS.includes(section)) {
          showSettingsSection("profile");
          openSettingsModal(section);
        } else {
          closeSettingsModal();
          showSettingsSection(section);
        }
      } else {
        closeSettingsModal();
      }
    }

    const settingsTabs = [...root.querySelectorAll("[data-settings-tab]")];
    const settingsPanels = [...root.querySelectorAll("[data-settings-panel]")];
    const settingsSectionKeys = settingsPanels.map((p) => p.getAttribute("data-settings-panel"));
    const MODAL_SECTIONS = ["privacy", "subscription"];
    const settingsModals = [...root.querySelectorAll("[data-settings-modal]")];

    function getSettingsSectionFromUrl() {
      const section = new URLSearchParams(window.location.search).get("section");
      if (MODAL_SECTIONS.includes(section)) return section;
      return settingsSectionKeys.includes(section) ? section : "profile";
    }

    function setSettingsUrlSection(key) {
      const url = new URL(window.location.href);
      if (!key || key === "profile") url.searchParams.delete("section");
      else url.searchParams.set("section", key);
      history.replaceState({}, "", url);
    }

    function closeSettingsModal() {
      settingsModals.forEach((modal) => {
        modal.hidden = true;
      });
      document.body.classList.remove("is-settings-modal");
      const section = new URLSearchParams(window.location.search).get("section");
      if (MODAL_SECTIONS.includes(section)) setSettingsUrlSection("");
    }

    function openSettingsModal(key) {
      if (!MODAL_SECTIONS.includes(key)) return;
      settingsModals.forEach((modal) => {
        modal.hidden = modal.getAttribute("data-settings-modal") !== key;
      });
      document.body.classList.add("is-settings-modal");
      setSettingsUrlSection(key);
      const dialog = root.querySelector(`[data-settings-modal="${key}"] .visit-settings-modal__dialog`);
      dialog?.querySelector("[data-settings-modal-close]")?.focus();
    }

    function showSettingsSection(key) {
      if (!settingsSectionKeys.includes(key)) key = "profile";
      closeSettingsModal();
      settingsTabs.forEach((tab) => {
        const on = tab.getAttribute("data-settings-tab") === key;
        tab.classList.toggle("is-active", on);
        tab.setAttribute("aria-selected", on ? "true" : "false");
      });
      settingsPanels.forEach((panel) => {
        const on = panel.getAttribute("data-settings-panel") === key;
        panel.hidden = !on;
      });
      setSettingsUrlSection(key);
    }

    settingsTabs.forEach((tab) => {
      tab.addEventListener("click", () => showSettingsSection(tab.getAttribute("data-settings-tab")));
    });

    root.querySelectorAll("[data-settings-modal-open]").forEach((btn) => {
      btn.addEventListener("click", () => openSettingsModal(btn.getAttribute("data-settings-modal-open")));
    });
    root.querySelectorAll("[data-settings-modal-close]").forEach((el) => {
      el.addEventListener("click", closeSettingsModal);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeSettingsModal();
    });

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
      const text = await res.text();
      let data = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        throw new Error(res.ok ? "Réponse invalide." : "Impossible de contacter le serveur.");
      }
      if (!res.ok || !data.ok) throw new Error(data.message || data.error || "Erreur");
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

    root.querySelectorAll("[data-interest], [data-trait], [data-value], [data-looking]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const on = btn.classList.toggle("is-on");
        btn.setAttribute("aria-pressed", on ? "true" : "false");
      });
    });
    root.querySelectorAll("[data-intent]").forEach((btn) => {
      btn.addEventListener("click", () => {
        root.querySelectorAll("[data-intent]").forEach((other) => other.classList.remove("is-on"));
        btn.classList.add("is-on");
      });
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
        life_project: fd.get("life_project"),
        bio: fd.get("bio"),
      });
      const first = String(fd.get("first_name") || "").trim().replace(/\s+/g, " ");
      const last = String(fd.get("last_name") || "").trim().replace(/\s+/g, " ");
      let name = first || last || "Membre";
      if (first && last && first.toLowerCase() !== last.toLowerCase() && !first.toLowerCase().endsWith(" " + last.toLowerCase())) {
        name = first + " " + last;
      }
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

    async function saveValues() {
      await postJSON("/api/profile/update/", {
        life_values: selected("[data-value]", "data-value"),
      });
    }

    async function saveLooking() {
      await postJSON("/api/profile/update/", {
        looking_for: selected("[data-looking]", "data-looking"),
        relationship_intent: root.querySelector("[data-intents] .is-on")?.getAttribute("data-intent") || "",
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
          push: true,
          likes: fd.get("likes") === "on",
          super_likes: fd.get("super_likes") === "on",
          matches: fd.get("matches") === "on",
          messages: fd.get("messages") === "on",
          status: fd.get("status") === "on",
        },
      });
    }

    function showNotifPrefs() {
      const enableWrap = root.querySelector("[data-notifs-enable-wrap]");
      const enableBtn = root.querySelector("[data-notifs-enable]");
      const activeBadge = root.querySelector("[data-notifs-active-badge]");
      const enableLead = root.querySelector("[data-notifs-enable-lead]");
      enableWrap?.setAttribute("hidden", "");
      enableBtn?.setAttribute("hidden", "");
      activeBadge?.setAttribute("hidden", "");
      enableLead?.setAttribute("hidden", "");
      root.querySelector("[data-notifs-prefs-wrap]")?.removeAttribute("hidden");
    }

    function showNotifEnable() {
      const enableWrap = root.querySelector("[data-notifs-enable-wrap]");
      const enableBtn = root.querySelector("[data-notifs-enable]");
      const activeBadge = root.querySelector("[data-notifs-active-badge]");
      const enableLead = root.querySelector("[data-notifs-enable-lead]");
      root.querySelector("[data-notifs-prefs-wrap]")?.setAttribute("hidden", "");
      enableWrap?.removeAttribute("hidden");
      enableBtn?.removeAttribute("hidden");
      activeBadge?.setAttribute("hidden", "");
      enableLead?.removeAttribute("hidden");
    }

    function showNotifActivatingSuccess() {
      const enableWrap = root.querySelector("[data-notifs-enable-wrap]");
      const enableBtn = root.querySelector("[data-notifs-enable]");
      const activeBadge = root.querySelector("[data-notifs-active-badge]");
      const enableLead = root.querySelector("[data-notifs-enable-lead]");
      enableWrap?.removeAttribute("hidden");
      enableBtn?.setAttribute("hidden", "");
      activeBadge?.removeAttribute("hidden");
      enableLead?.setAttribute("hidden", "");
      window.setTimeout(showNotifPrefs, 900);
    }

    function setNotifEnableMsg(text, isError) {
      const msg = root.querySelector("[data-notifs-enable-msg]");
      if (!msg) return;
      msg.textContent = text || "";
      msg.hidden = !text;
      msg.classList.toggle("is-error", Boolean(isError));
    }

    async function enableNotifications() {
      setNotifEnableMsg("");
      if (typeof window.timaloveEnablePush !== "function") {
        throw new Error("Module notifications indisponible.");
      }
      await window.timaloveEnablePush();
      await postJSON("/api/profile/update/", {
        notification_preferences: {
          push: true,
          likes: true,
          super_likes: true,
          matches: true,
          messages: true,
          status: true,
        },
      });
      const form = root.querySelector("[data-notifs-form]");
      form?.querySelectorAll('input[type="checkbox"]').forEach((input) => {
        input.checked = true;
      });
      showNotifActivatingSuccess();
    }

    async function disableNotifications() {
      if (typeof window.timaloveDisablePush === "function") {
        await window.timaloveDisablePush().catch(() => { });
      }
      await postJSON("/api/profile/update/", {
        notification_preferences: {
          push: false,
          likes: false,
          super_likes: false,
          matches: false,
          messages: false,
          status: false,
        },
      });
      showNotifEnable();
      setNotifEnableMsg("");
    }

    const prefsWrap = root.querySelector("[data-notifs-prefs-wrap]");
    if (prefsWrap && !prefsWrap.hasAttribute("hidden")) {
      showNotifPrefs();
    }

    root.querySelector("[data-notifs-enable]")?.addEventListener("click", async (e) => {
      const btn = e.currentTarget;
      btn.disabled = true;
      setNotifEnableMsg("");
      try {
        await enableNotifications();
        window.timaloveNotifPopup?.showSuccess(
          "Vous recevrez les likes, matchs et messages en temps réel.",
        );
      } catch (err) {
        setNotifEnableMsg(err.message || "Activation impossible.", true);
      } finally {
        btn.disabled = false;
      }
    });

    root.querySelector("[data-notifs-disable]")?.addEventListener("click", (e) => {
      if (!window.confirm("Désactiver toutes les notifications push ?")) return;
      void withButton(e.currentTarget, "notifications", disableNotifications, "Notifications désactivées.");
    });

    root.querySelector("[data-notifs-test]")?.addEventListener("click", (e) => {
      void withButton(e.currentTarget, "notifications", async () => {
        const data = await postJSON("/api/push/test/", {});
        window.timaloveNotifPopup?.showSuccess(
          data.message || "Notification test envoyée. Vérifiez votre appareil.",
        );
      }, "Envoi du test…");
    });

    const wsTestBtn = root.querySelector("[data-ws-test]");
    const wsTestMsg = root.querySelector("[data-ws-test-msg]");
    const wsTestUrl = root.querySelector("[data-ws-test-url]");

    function setWsTestMsg(text, isError) {
      if (!wsTestMsg) return;
      wsTestMsg.textContent = text || "";
      wsTestMsg.hidden = !text;
      wsTestMsg.classList.toggle("is-error", Boolean(isError));
    }

    function wsNotificationsUrl() {
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      return `${proto}//${window.location.host}/ws/notifications/`;
    }

    if (wsTestUrl) {
      wsTestUrl.textContent = `Endpoint : ${wsNotificationsUrl()}`;
    }

    wsTestBtn?.addEventListener("click", () => {
      if (wsTestBtn.disabled) return;
      const url = wsNotificationsUrl();
      setWsTestMsg("Connexion en cours…", false);
      wsTestBtn.disabled = true;
      console.info("[TimaLove WS test] Démarrage", url);

      let settled = false;
      let ws;
      const finish = (text, isError) => {
        if (settled) return;
        settled = true;
        window.clearTimeout(wsTestBtn._wsTimer);
        wsTestBtn.disabled = false;
        setWsTestMsg(text, isError);
      };

      try {
        ws = new WebSocket(url);
      } catch (err) {
        console.error("[TimaLove WS test] Impossible d'ouvrir la connexion", err);
        finish(err.message || "Connexion impossible.", true);
        return;
      }

      wsTestBtn._wsTimer = window.setTimeout(() => {
        console.warn("[TimaLove WS test] Délai dépassé (8 s)");
        try {
          ws.close();
        } catch (_) {
          /* ignore */
        }
        finish("Délai dépassé — vérifiez que Daphne tourne.", true);
      }, 8000);

      ws.onopen = () => {
        console.log("[TimaLove WS test] WS OK — connexion ouverte");
        finish("WS OK — connexion WebSocket réussie. Voir la console (F12).", false);
        window.setTimeout(() => {
          try {
            ws.close();
          } catch (_) {
            /* ignore */
          }
        }, 1200);
      };

      ws.onmessage = (event) => {
        console.log("[TimaLove WS test] Notif reçue:", event.data);
      };

      ws.onerror = () => {
        console.error("[TimaLove WS test] Erreur WebSocket");
        finish("Erreur WebSocket — consultez la console (F12).", true);
      };

      ws.onclose = (event) => {
        console.log("[TimaLove WS test] Fermé", event.code, event.reason || "");
        if (!settled && event.code !== 1000) {
          const hint =
            event.code === 1006
              ? "Connexion refusée — lancez Daphne et vérifiez que vous êtes connecté."
              : `Connexion fermée (code ${event.code}).`;
          finish(hint, true);
        }
      };
    });

    root.querySelector('[data-save="identity"]')?.addEventListener("click", (e) => {
      void withButton(e.currentTarget, "identity", saveIdentity, "Profil enregistré.");
    });

    const emailView = root.querySelector("[data-email-view]");
    const emailForm = root.querySelector("[data-email-form]");
    const emailDisplay = root.querySelector("[data-email-display]");
    const emailInput = root.querySelector("[data-email-input]");

    function closeEmailEditor() {
      if (!emailForm || !emailView) return;
      emailForm.hidden = true;
      emailView.hidden = false;
      const pwd = emailForm.querySelector("[data-email-password]");
      if (pwd) pwd.value = "";
      if (emailInput && emailDisplay) emailInput.value = emailDisplay.value || "";
    }

    root.querySelector("[data-email-edit]")?.addEventListener("click", () => {
      if (!emailForm || !emailView) return;
      emailView.hidden = true;
      emailForm.hidden = false;
      emailForm.querySelector("[data-email-input]")?.focus();
    });

    root.querySelector("[data-email-cancel]")?.addEventListener("click", closeEmailEditor);

    async function saveEmail() {
      if (!emailForm) return;
      const email = (emailInput?.value || "").trim();
      const password = (emailForm.querySelector("[data-email-password]")?.value || "").trim();
      if (!email) throw new Error("Saisissez une adresse email.");
      if (!password) throw new Error("Confirmez avec votre mot de passe actuel.");
      const data = await postJSON("/api/profile/email/", { email, current_password: password });
      if (emailDisplay) emailDisplay.value = data.email || email;
      if (emailInput) emailInput.value = data.email || email;
      closeEmailEditor();
    }

    root.querySelector('[data-save="email"]')?.addEventListener("click", (e) => {
      void withButton(e.currentTarget, "email", saveEmail, "Email mis à jour.");
    });

    const phoneView = root.querySelector("[data-phone-view]");
    const phoneForm = root.querySelector("[data-phone-form]");
    const phoneDisplay = root.querySelector("[data-phone-display]");
    const phoneInput = root.querySelector("[data-phone-input]");

    function closePhoneEditor() {
      if (!phoneForm || !phoneView) return;
      phoneForm.hidden = true;
      phoneView.hidden = false;
      if (phoneInput && phoneDisplay) phoneInput.value = phoneDisplay.value || "";
    }

    root.querySelector("[data-phone-edit]")?.addEventListener("click", () => {
      if (!phoneForm || !phoneView) return;
      phoneView.hidden = true;
      phoneForm.hidden = false;
      phoneInput?.focus();
    });

    root.querySelector("[data-phone-cancel]")?.addEventListener("click", closePhoneEditor);

    async function savePhone() {
      if (!phoneForm) return;
      const phone = (phoneInput?.value || "").trim();
      if (!phone) throw new Error("Saisissez un numéro de téléphone.");
      await postJSON("/api/profile/update/", { phone });
      if (phoneDisplay) phoneDisplay.value = phone;
      closePhoneEditor();
    }

    root.querySelector('[data-save="phone"]')?.addEventListener("click", (e) => {
      void withButton(e.currentTarget, "phone", savePhone, "Téléphone mis à jour.");
    });

    async function savePassword() {
      const block = root.querySelector("[data-password-form]");
      if (!block) return;
      const current = (block.querySelector("[data-password-current]")?.value || "").trim();
      const next = (block.querySelector("[data-password-new]")?.value || "").trim();
      const confirm = (block.querySelector("[data-password-confirm]")?.value || "").trim();
      if (!current || !next || !confirm) throw new Error("Complétez tous les champs du mot de passe.");
      if (next.length < 8) throw new Error("Le nouveau mot de passe doit contenir au moins 8 caractères.");
      await postJSON("/api/profile/password/", {
        current_password: current,
        new_password: next,
        confirm_password: confirm,
      });
      block.querySelectorAll("input[type='password']").forEach((input) => {
        input.value = "";
      });
    }

    root.querySelector('[data-save="password"]')?.addEventListener("click", (e) => {
      void withButton(e.currentTarget, "password", savePassword, "Mot de passe mis à jour.");
    });

    root.querySelectorAll("[data-password-toggle]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const name = btn.getAttribute("data-password-toggle");
        const input = root.querySelector('[name="' + name + '"]');
        if (!input) return;
        const reveal = input.type === "password";
        input.type = reveal ? "text" : "password";
        btn.setAttribute("aria-label", reveal ? "Masquer le mot de passe" : "Afficher le mot de passe");
      });
    });

    function setSelectByLabel(select, label) {
      if (!select || !label) return false;
      const target = String(label).trim().toLowerCase();
      for (const option of select.options) {
        if (option.value.trim().toLowerCase() === target) {
          select.value = option.value;
          return true;
        }
      }
      return false;
    }

    root.querySelector("[data-geo-locate]")?.addEventListener("click", (e) => {
      const btn = e.currentTarget;
      const statusEl = root.querySelector("[data-geo-status]");
      if (!navigator.geolocation) {
        setMsg("location", "La géolocalisation n’est pas disponible sur cet appareil.", true);
        return;
      }
      btn.disabled = true;
      if (statusEl) {
        statusEl.hidden = false;
        statusEl.textContent = "Recherche de votre position…";
        statusEl.classList.remove("is-error");
      }
      navigator.geolocation.getCurrentPosition(
        async (pos) => {
          try {
            const data = await postJSON("/api/auth/signup/location/", {
              latitude: pos.coords.latitude,
              longitude: pos.coords.longitude,
            });
            if (!data.ok) throw new Error(data.message || "Position impossible.");
            const cityInput = profileForm?.querySelector("[data-geo-city]");
            const communeInput = profileForm?.querySelector("[data-geo-commune]");
            const residenceSelect = profileForm?.querySelector("[data-geo-residence]");
            if (cityInput && data.city) cityInput.value = data.city;
            if (communeInput && data.commune) communeInput.value = data.commune;
            if (residenceSelect && data.country) setSelectByLabel(residenceSelect, data.country);
            const loc = [communeInput?.value || "", cityInput?.value || "", residenceSelect?.value || ""].filter(Boolean).join(", ");
            const locEl = root.querySelector("[data-display-location]");
            if (locEl && loc) locEl.textContent = loc;
            if (statusEl) {
              statusEl.textContent = data.display || "Position détectée — vérifiez puis enregistrez le profil.";
            }
            setMsg("location", "Localisation détectée. Enregistrez pour confirmer.", false);
          } catch (err) {
            if (statusEl) {
              statusEl.textContent = err.message;
              statusEl.classList.add("is-error");
            }
            setMsg("location", err.message, true);
          } finally {
            btn.disabled = false;
          }
        },
        () => {
          if (statusEl) {
            statusEl.hidden = false;
            statusEl.textContent = "Autorisez la localisation dans votre navigateur.";
            statusEl.classList.add("is-error");
          }
          setMsg("location", "Autorisez la localisation pour continuer.", true);
          btn.disabled = false;
        },
        { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 }
      );
    });
    root.querySelector('[data-save="interests"]')?.addEventListener("click", (e) => {
      void withButton(e.currentTarget, "interests", saveInterests, "Intérêts enregistrés.");
    });
    root.querySelector('[data-save="values"]')?.addEventListener("click", (e) => {
      void withButton(e.currentTarget, "values", saveValues, "Valeurs enregistrées.");
    });
    root.querySelector('[data-save="looking"]')?.addEventListener("click", (e) => {
      void withButton(e.currentTarget, "looking", saveLooking, "Profil recherché enregistré.");
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

    root.addEventListener("click", (event) => {
      const btn = event.target.closest("[data-checkout]");
      if (!btn || !root.contains(btn) || btn.disabled) return;
      const original = btn.textContent;
      void withButton(
        btn,
        "subscription",
        async () => {
          btn.textContent = "Ouverture du paiement…";
          const data = await postJSON("/api/payments/checkout/", { tier: btn.getAttribute("data-checkout") });
          if (!data.checkout_url) throw new Error(data.message || "Lien de paiement indisponible.");
          window.location.href = data.checkout_url;
        },
        "Redirection vers le paiement…"
      ).finally(() => {
        if (document.body.contains(btn)) btn.textContent = original;
      });
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
      if (flag) flag.hidden = !hasPhoto;
    }

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
