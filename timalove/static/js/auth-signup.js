/**
 * TimaLove — inscription interactive (slides) sur /connexion/.
 */
(function () {
  const DRAFT_KEY = "tl_signup_draft";
  const EMAIL_STEPS = ["email", "password", "identity", "socio", "interests", "bios", "projet", "photos", "geo", "notif"];
  const PHONE_STEPS = ["phone", "password", "identity", "socio", "interests", "bios", "projet", "photos", "geo", "notif"];
  const OAUTH_STEPS = ["identity", "socio", "interests", "bios", "projet", "photos", "geo", "notif"];
  const SKIP_HIDDEN_STEPS = ["email", "phone", "password", "identity", "socio", "photos"];
  const CTAS = {
    email: "Continuer",
    phone: "Continuer",
    password: "Continuer",
    identity: "Continuer",
    socio: "Continuer",
    interests: "Continuer",
    bios: "Continuer",
    projet: "Continuer",
    photos: "Continuer",
    geo: "Continuer",
    notif: "Rejoindre TimaLove",
  };

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

  function cookie(name) {
    const match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[1]) : "";
  }

  function csrf() {
    return cookie("csrftoken");
  }

  function readPrefill() {
    const node = document.getElementById("signup-prefill");
    if (!node) return {};
    try {
      return JSON.parse(node.textContent || "{}") || {};
    } catch {
      return {};
    }
  }

  function loadDraft() {
    try {
      return JSON.parse(sessionStorage.getItem(DRAFT_KEY) || "{}") || {};
    } catch {
      return {};
    }
  }

  function saveDraft(draft) {
    try {
      sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
    } catch {
      /* quota photos : on garde en mémoire */
    }
  }

  function clearDraft() {
    sessionStorage.removeItem(DRAFT_KEY);
  }

  function e164(iti, input) {
    const raw = (input?.value || "").trim();
    if (!raw) return "";
    if (iti && typeof iti.getNumber === "function") {
      const number = iti.getNumber();
      if (number) return number;
    }
    return raw;
  }

  function compressImage(file) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      const url = URL.createObjectURL(file);
      img.onload = () => {
        const max = 1200;
        let { width, height } = img;
        if (width > max || height > max) {
          const ratio = Math.min(max / width, max / height);
          width = Math.round(width * ratio);
          height = Math.round(height * ratio);
        }
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        canvas.getContext("2d").drawImage(img, 0, 0, width, height);
        URL.revokeObjectURL(url);
        resolve(canvas.toDataURL("image/jpeg", 0.78));
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error("Image illisible."));
      };
      img.src = url;
    });
  }

  async function getFcmToken() {
    if (typeof window.timaloveEnablePush !== "function") return "";
    try {
      const result = await window.timaloveEnablePush({ skipRegisterOnFailure: true });
      return result.token || "";
    } catch {
      return "";
    }
  }

  const api = {
    showChoice() {},
    showLogin() {},
    startChannel() {},
    startOauth() {},
  };
  window.TimaLoveSignup = api;

  document.addEventListener("DOMContentLoaded", () => {
    const panel = document.querySelector("[data-auth-panel]");
    const wizard = document.querySelector("[data-signup-wizard]");
    if (!panel || !wizard) return;

    const statusEl = document.querySelector("[data-auth-status]");
    const hearts = document.querySelector("[data-auth-hearts]");
    const heart = wizard.querySelector("[data-signup-heart]");
    const progress = wizard.querySelector("[data-signup-progress]");
    const nextBtn = wizard.querySelector("[data-signup-next]");
    const skipBtn = wizard.querySelector("[data-signup-skip]");
    const views = {
      login: panel.querySelector('[data-auth-view="login"]'),
      choice: panel.querySelector('[data-auth-view="choice"]'),
      wizard,
    };

    let draft = Object.assign({ channel: "email" }, loadDraft(), readPrefill());
    let steps = EMAIL_STEPS;
    let index = 0;
    let busy = false;
    let phoneIti = null;
    let identityIti = null;
    const nextUrl = panel.getAttribute("data-next") || "";

    function setStatus(message, isError) {
      if (!statusEl) return;
      statusEl.hidden = !message;
      statusEl.textContent = message || "";
      statusEl.classList.toggle("is-error", Boolean(isError));
    }

    function showView(name) {
      Object.entries(views).forEach(([key, node]) => {
        if (!node) return;
        node.hidden = key !== name;
      });
      panel.setAttribute("data-view", name);
      hearts?.classList.toggle("is-wizard", name === "wizard");
      if (name !== "wizard") {
        hearts?.style.setProperty("--beat", "1");
      }
    }

    function currentStep() {
      return steps[index] || steps[0];
    }

    function setBeat() {
      const beat = Math.max(1, Math.min(10, Math.round(((index + 1) / steps.length) * 10)));
      heart?.style.setProperty("--beat", String(beat));
      hearts?.style.setProperty("--beat", String(beat));
      if (progress) progress.textContent = `${index + 1}/${steps.length}`;
      if (nextBtn) nextBtn.textContent = CTAS[currentStep()] || "Continuer";
      if (skipBtn) skipBtn.hidden = SKIP_HIDDEN_STEPS.includes(currentStep());
    }

    function clearErrors(scope) {
      (scope || wizard).querySelectorAll(".is-invalid").forEach((el) => el.classList.remove("is-invalid"));
      (scope || wizard).querySelectorAll("[data-error-for]").forEach((el) => {
        el.hidden = true;
        el.textContent = "";
      });
    }

    function showErrors(errors) {
      clearErrors();
      Object.entries(errors || {}).forEach(([field, message]) => {
        if (field === "_form") {
          setStatus(message, true);
          return;
        }
        const err = wizard.querySelector(`[data-error-for="${field}"]`);
        if (err) {
          err.hidden = false;
          err.textContent = message;
        }
        const input =
          wizard.querySelector(`[data-field="${field}"]`) ||
          wizard.querySelector(`[data-signup-slide="${currentStep()}"] [data-error-for="${field}"]`)?.previousElementSibling;
        const slide = wizard.querySelector(`[data-signup-slide="${currentStep()}"]`);
        const fieldInput = slide?.querySelector(`[data-field="${field}"]`);
        (fieldInput || input)?.classList.add("is-invalid");
        if (field === "phone") {
          slide?.querySelector("input[type='tel']")?.classList.add("is-invalid");
        }
        if (field === "photos") {
          wizard.querySelector(".signup-photos")?.classList.add("is-invalid");
        }
      });
      if (!errors?._form) {
        const first = Object.values(errors || {})[0];
        if (first) setStatus(first, true);
      }
    }

    function selected(listSel, attr) {
      return [...wizard.querySelectorAll(`${listSel} .is-on`)].map((btn) => btn.getAttribute(attr)).filter(Boolean);
    }

    function collectIdentityPhone() {
      const fromIti = e164(identityIti, wizard.querySelector("[data-signup-identity-phone]"));
      return fromIti || draft.phone || "";
    }

    function collectSlideIntoDraft() {
      const step = currentStep();
      const slide = wizard.querySelector(`[data-signup-slide="${step}"]`);
      if (!slide) return;
      if (step === "email") draft.email = (slide.querySelector("[data-field='email']")?.value || "").trim();
      if (step === "phone") draft.phone = e164(phoneIti, slide.querySelector("[data-signup-phone]"));
      if (step === "password") draft.password = slide.querySelector("[data-field='password']")?.value || "";
      if (step === "identity") {
        draft.last_name = (slide.querySelector("[data-field='last_name']")?.value || "").trim();
        draft.first_name = (slide.querySelector("[data-field='first_name']")?.value || "").trim();
        draft.age = slide.querySelector("[data-field='age']")?.value || "";
        draft.phone = collectIdentityPhone();
        const optionalEmail = (slide.querySelector("[data-identity-email] [data-field='email']")?.value || "").trim();
        if (optionalEmail) draft.email = optionalEmail;
      }
      if (step === "socio") {
        draft.gender = slide.querySelector("[data-field='gender']")?.value || "";
        draft.religion = slide.querySelector("[data-field='religion']")?.value || "";
        draft.country = (slide.querySelector("[data-combo-value]")?.value || "").trim();
      }
      if (step === "interests") {
        draft.interests = selected("[data-interests]", "data-interest");
        draft.personality_traits = selected("[data-traits]", "data-trait");
        draft.life_values = selected("[data-values]", "data-value");
      }
      if (step === "bios") {
        draft.bio = (slide.querySelector("[data-field='bio']")?.value || "").trim();
        draft.looking_for = selected("[data-looking-for]", "data-looking");
        draft.relationship_intent = wizard.querySelector("[data-intents] .is-on")?.getAttribute("data-intent") || "";
      }
      if (step === "projet") {
        draft.life_project = (slide.querySelector("[data-field='life_project']")?.value || "").trim();
      }
      if (step === "geo") {
        draft.city = (slide.querySelector("[data-field='city']")?.value || "").trim();
        draft.geo_country = (slide.querySelector("[data-field='geo_country']")?.value || "").trim();
        draft.residence_country = draft.geo_country;
        draft.commune = (slide.querySelector("[data-field='commune']")?.value || "").trim();
      }
      draft.channel = draft.channel || "email";
      saveDraft(draft);
    }

    function fillSlide(step) {
      const slide = wizard.querySelector(`[data-signup-slide="${step}"]`);
      if (!slide) return;
      const setVal = (sel, value) => {
        const el = slide.querySelector(sel);
        if (el && value != null && value !== "") el.value = value;
      };
      setVal("[data-field='email']", draft.email);
      setVal("[data-field='password']", draft.password);
      setVal("[data-field='last_name']", draft.last_name);
      setVal("[data-field='first_name']", draft.first_name);
      setVal("[data-field='age']", draft.age);
      setVal("[data-field='gender']", draft.gender);
      setVal("[data-field='religion']", draft.religion);
      setVal("[data-field='bio']", draft.bio);
      setVal("[data-field='life_project']", draft.life_project);
      setVal("[data-field='city']", draft.city);
      setVal("[data-field='geo_country']", draft.geo_country || draft.residence_country);
      setVal("[data-field='commune']", draft.commune);
      if (draft.country) {
        const comboInput = slide.querySelector("[data-combo-input]");
        const comboVal = slide.querySelector("[data-combo-value]");
        if (comboInput) comboInput.value = draft.country;
        if (comboVal) comboVal.value = draft.country;
      }
      if (phoneIti && draft.phone && step === "phone") phoneIti.setNumber(draft.phone);
      if (identityIti && draft.phone && step === "identity") identityIti.setNumber(draft.phone);
      function syncPressed(btn, on) {
        btn.classList.toggle("is-on", on);
        btn.setAttribute("aria-pressed", on ? "true" : "false");
      }
      wizard.querySelectorAll("[data-interest]").forEach((btn) => {
        syncPressed(btn, (draft.interests || []).includes(btn.getAttribute("data-interest")));
      });
      wizard.querySelectorAll("[data-trait]").forEach((btn) => {
        syncPressed(btn, (draft.personality_traits || []).includes(btn.getAttribute("data-trait")));
      });
      wizard.querySelectorAll("[data-value]").forEach((btn) => {
        const id = btn.getAttribute("data-value");
        const values = draft.life_values || [];
        syncPressed(btn, values.includes(id) || values.includes(btn.textContent.trim()));
      });
      const lookingIds = Array.isArray(draft.looking_for) ? draft.looking_for : [];
      wizard.querySelectorAll("[data-looking]").forEach((btn) => {
        syncPressed(btn, lookingIds.includes(btn.getAttribute("data-looking")));
      });
      wizard.querySelectorAll("[data-intent]").forEach((btn) => {
        btn.classList.toggle("is-on", draft.relationship_intent === btn.getAttribute("data-intent"));
      });
      renderPhoto(1, draft.photo_data_url || draft.photo_url);
      renderPhoto(2, draft.photo_data_url_2 || draft.photo_url_2);
      if ((draft.city || draft.commune) && step === "geo") {
        const fields = wizard.querySelector("[data-geo-fields]");
        if (fields) fields.hidden = false;
      }
    }

    function renderPhoto(slot, src) {
      const img = wizard.querySelector(`[data-photo-preview="${slot}"]`);
      const placeholder = wizard.querySelector(`[data-photo-placeholder="${slot}"]`);
      if (!img) return;
      if (src) {
        img.src = src;
        img.hidden = false;
        if (placeholder) placeholder.hidden = true;
      }
    }

    function toggleIdentityFields() {
      const emailWrap = wizard.querySelector("[data-identity-email]");
      if (!emailWrap) return;
      const oauthEmail = (draft.email || "").trim();
      const oauthHasEmail = draft.channel === "oauth" && oauthEmail.includes("@");
      if (oauthHasEmail) {
        emailWrap.hidden = true;
        const input = emailWrap.querySelector("[data-field='email']");
        if (input) input.value = oauthEmail;
        return;
      }
      emailWrap.hidden = draft.channel !== "phone";
    }

    function showSlide(i, fromRight) {
      index = Math.max(0, Math.min(i, steps.length - 1));
      const id = currentStep();
      wizard.querySelectorAll("[data-signup-slide]").forEach((slide) => {
        const on = slide.getAttribute("data-signup-slide") === id;
        slide.classList.toggle("is-active", on);
        slide.classList.toggle("is-from-right", on && fromRight !== false);
        slide.classList.toggle("is-from-left", on && fromRight === false);
        slide.setAttribute("aria-hidden", on ? "false" : "true");
      });
      toggleIdentityFields();
      fillSlide(id);
      setBeat();
      clearErrors();
      setStatus("", false);
      if (id === "phone") ensurePhoneIti();
      if (id === "identity") ensureIdentityIti();
    }

    function ensurePhoneIti() {
      const input = wizard.querySelector("[data-signup-phone]");
      if (!input || !window.intlTelInput || phoneIti) return;
      phoneIti = window.intlTelInput(input, {
        initialCountry: "auto",
        geoIpLookup: (cb) => {
          fetch("https://ipapi.co/json/")
            .then((r) => r.json())
            .then((d) => cb((d.country_code || "sn").toLowerCase()))
            .catch(() => cb("sn"));
        },
        separateDialCode: true,
        nationalMode: true,
        preferredCountries: ["sn", "ci", "ml", "gn", "fr", "be", "cm", "ma"],
        utilsScript: "https://cdn.jsdelivr.net/npm/intl-tel-input@24.6.0/build/js/utils.js",
      });
      if (draft.phone) phoneIti.setNumber(draft.phone);
    }

    function ensureIdentityIti() {
      const input = wizard.querySelector("[data-signup-identity-phone]");
      if (!input || !window.intlTelInput || identityIti) return;
      identityIti = window.intlTelInput(input, {
        initialCountry: "auto",
        geoIpLookup: (cb) => {
          fetch("https://ipapi.co/json/")
            .then((r) => r.json())
            .then((d) => cb((d.country_code || "sn").toLowerCase()))
            .catch(() => cb("sn"));
        },
        separateDialCode: true,
        nationalMode: true,
        preferredCountries: ["sn", "ci", "ml", "gn", "fr", "be", "cm", "ma"],
        utilsScript: "https://cdn.jsdelivr.net/npm/intl-tel-input@24.6.0/build/js/utils.js",
      });
      if (draft.phone) identityIti.setNumber(draft.phone);
    }

    function localValidate(step) {
      const errors = {};
      if (step === "email") {
        const email = (draft.email || "").trim();
        if (!email || !email.includes("@")) errors.email = "Indiquez un email valide.";
      }
      if (step === "phone") {
        if (!draft.phone) errors.phone = "Indiquez un numéro de téléphone valide.";
      }
      if (step === "password" && draft.channel !== "oauth") {
        if ((draft.password || "").length < 8) errors.password = "Le mot de passe doit contenir au moins 8 caractères.";
      }
      if (step === "identity") {
        if (!(draft.first_name || "").trim()) errors.first_name = "Le prénom est obligatoire.";
        if (!(draft.last_name || "").trim()) errors.last_name = "Le nom est obligatoire.";
        const age = Number(draft.age);
        if (!age || age < 18) errors.age = "Vous devez avoir au moins 18 ans.";
        else if (age > 99) errors.age = "Vérifiez l’âge saisi.";
        if (draft.channel !== "phone" && !draft.phone) errors.phone = "Indiquez un numéro de téléphone valide.";
      }
      if (step === "socio") {
        if (!draft.gender || (draft.gender !== "male" && draft.gender !== "female")) {
          errors.gender = "Le genre est obligatoire. Choisissez Homme ou Femme.";
        }
        if (!draft.religion) errors.religion = "Sélectionnez votre religion.";
        if (!draft.country) errors.country = "Sélectionnez votre pays d’origine dans la liste.";
      }
      if (step === "photos") {
        if (!(draft.photo_data_url || draft.photo_url)) errors.photos = "Ajoutez au moins une photo de profil.";
      }
      return errors;
    }

    async function checkIdentifier(payload) {
      const res = await fetch("/api/auth/signup/check/", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.ok === false) return data.errors || { _form: data.message || "Vérification impossible." };
      return {};
    }

    async function goNext() {
      if (busy) return;
      collectSlideIntoDraft();
      const step = currentStep();
      const errors = localValidate(step);
      if (Object.keys(errors).length) {
        showErrors(errors);
        return;
      }
      if (step === "email" || step === "phone" || (step === "identity" && (draft.phone || draft.email))) {
        busy = true;
        nextBtn.disabled = true;
        const remote = await checkIdentifier({ email: draft.email, phone: draft.phone });
        busy = false;
        nextBtn.disabled = false;
        if (Object.keys(remote).length) {
          showErrors(remote);
          return;
        }
      }
      if (step === "notif") {
        await completeSignup();
        return;
      }
      showSlide(index + 1, true);
    }

    function goBack() {
      if (index <= 0) {
        if (draft.channel === "oauth") return;
        showView("choice");
        return;
      }
      collectSlideIntoDraft();
      showSlide(index - 1, false);
    }

    function gotoStepName(name) {
      const i = steps.indexOf(name);
      if (i >= 0) showSlide(i, true);
    }

    async function completeSignup() {
      busy = true;
      nextBtn.disabled = true;
      setStatus("Création du compte…", false);
      const payload = Object.assign({}, draft, { next: nextUrl });
      try {
        const res = await fetch("/api/auth/signup/complete/", {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
          body: JSON.stringify(payload),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.ok) {
          saveDraft(draft);
          if (data.step) gotoStepName(data.step);
          showErrors(data.errors || { _form: data.message || "Inscription interrompue." });
          return;
        }
        clearDraft();
        if (window.TimaLoveTransit?.start) {
          window.TimaLoveTransit.start(data.redirect || "/explorer/");
        } else {
          window.location.href = data.redirect || "/explorer/";
        }
        return;
      } catch (err) {
        saveDraft(draft);
        setStatus(err.message || "Inscription interrompue. Réessayez.", true);
      } finally {
        busy = false;
        nextBtn.disabled = false;
      }
    }

    function startChannel(channel) {
      draft = Object.assign({}, loadDraft(), { channel });
      if (channel === "email") steps = EMAIL_STEPS;
      else if (channel === "phone") steps = PHONE_STEPS;
      else steps = OAUTH_STEPS;
      saveDraft(draft);
      showView("wizard");
      showSlide(0, true);
    }

    function startOauth(profile) {
      draft = Object.assign({}, loadDraft(), profile || {}, { channel: "oauth" });
      steps = OAUTH_STEPS.filter((step) => {
        if (step === "email" && (draft.email || "").includes("@")) return false;
        return true;
      });
      saveDraft(draft);
      showView("wizard");
      showSlide(0, true);
    }

    api.showChoice = () => {
      showView("choice");
      setStatus("", false);
    };
    api.showLogin = () => {
      showView("login");
      setStatus("", false);
    };
    api.startChannel = startChannel;
    api.startOauth = startOauth;

    document.querySelectorAll("[data-auth-open-signup]").forEach((btn) => {
      btn.addEventListener("click", (event) => {
        event.preventDefault();
        api.showChoice();
      });
    });
    document.querySelectorAll("[data-auth-back-login]").forEach((btn) => {
      btn.addEventListener("click", (event) => {
        event.preventDefault();
        api.showLogin();
      });
    });
    document.querySelectorAll("[data-signup-channel]").forEach((btn) => {
      btn.addEventListener("click", () => startChannel(btn.getAttribute("data-signup-channel")));
    });
    wizard.querySelector("[data-signup-back]")?.addEventListener("click", goBack);
    nextBtn?.addEventListener("click", () => void goNext());

    document.querySelectorAll("[data-icon]").forEach((el) => {
      el.innerHTML = ICONS[el.dataset.icon] || "";
    });

    document.querySelectorAll("[data-password-toggle]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const input = document.getElementById(btn.getAttribute("data-password-toggle"));
        if (!input) return;
        const reveal = input.type === "password";
        input.type = reveal ? "text" : "password";
        btn.classList.toggle("is-revealed", reveal);
        btn.setAttribute("aria-label", reveal ? "Masquer le mot de passe" : "Afficher le mot de passe");
      });
    });

    wizard.querySelectorAll("[data-signup-skip]").forEach((btn) => {
      btn.addEventListener("click", () => {
        collectSlideIntoDraft();
        const step = currentStep();
        if (step === "notif") {
          void completeSignup();
          return;
        }
        if (["interests", "bios", "projet", "geo"].includes(step)) {
          if (step === "socio") return;
          showSlide(index + 1, true);
          return;
        }
        void goNext();
      });
    });

    wizard.querySelectorAll("[data-interest], [data-trait], [data-value], [data-looking]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const on = btn.classList.toggle("is-on");
        btn.setAttribute("aria-pressed", on ? "true" : "false");
      });
    });
    wizard.querySelectorAll("[data-intent]").forEach((btn) => {
      btn.addEventListener("click", () => {
        wizard.querySelectorAll("[data-intent]").forEach((other) => other.classList.remove("is-on"));
        btn.classList.add("is-on");
      });
    });

    const combo = wizard.querySelector("[data-combo]");
    if (combo) {
      const input = combo.querySelector("[data-combo-input]");
      const hidden = combo.querySelector("[data-combo-value]");
      const list = combo.querySelector("[data-combo-list]");
      const items = [...list.querySelectorAll("[data-combo-item]")];
      function fold(value) {
        return (value || "")
          .toLowerCase()
          .normalize("NFD")
          .replace(/[\u0300-\u036f]/g, "")
          .trim();
      }
      function filter() {
        const q = fold(input.value);
        let visible = 0;
        items.forEach((btn) => {
          const ok = !q || fold(btn.textContent).includes(q);
          btn.parentElement.hidden = !ok;
          if (ok) visible += 1;
        });
        list.hidden = visible === 0;
      }
      input?.addEventListener("focus", () => {
        list.hidden = false;
        filter();
      });
      input?.addEventListener("input", () => {
        hidden.value = "";
        filter();
      });
      list?.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-combo-item]");
        if (!btn) return;
        input.value = btn.textContent;
        hidden.value = btn.textContent.trim();
        list.hidden = true;
      });
      document.addEventListener("click", (event) => {
        if (!combo.contains(event.target)) list.hidden = true;
      });
    }

    wizard.querySelectorAll("[data-photo-file]").forEach((input) => {
      input.addEventListener("change", async () => {
        const file = input.files?.[0];
        const slot = input.getAttribute("data-photo-file");
        if (!file || !slot) return;
        try {
          const dataUrl = await compressImage(file);
          if (slot === "1") {
            draft.photo_data_url = dataUrl;
            draft.photo_url = dataUrl;
          } else {
            draft.photo_data_url_2 = dataUrl;
            draft.photo_url_2 = dataUrl;
          }
          saveDraft(draft);
          renderPhoto(slot, dataUrl);
        } catch (err) {
          setStatus(err.message || "Image illisible.", true);
        }
      });
    });

    wizard.querySelector("[data-geo-enable]")?.addEventListener("click", () => {
      if (!navigator.geolocation) {
        showErrors({ geo: "La géolocalisation n’est pas disponible sur cet appareil." });
        return;
      }
      setStatus("Recherche de votre position…", false);
      navigator.geolocation.getCurrentPosition(
        async (pos) => {
          try {
            const res = await fetch("/api/auth/signup/location/", {
              method: "POST",
              credentials: "same-origin",
              headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
              body: JSON.stringify({
                latitude: pos.coords.latitude,
                longitude: pos.coords.longitude,
              }),
            });
            const data = await res.json().catch(() => ({}));
            draft.latitude = data.latitude || pos.coords.latitude;
            draft.longitude = data.longitude || pos.coords.longitude;
            draft.city = data.city || "";
            draft.geo_country = data.country || "";
            draft.residence_country = data.country || "";
            draft.commune = data.commune || "";
            saveDraft(draft);
            const fields = wizard.querySelector("[data-geo-fields]");
            if (fields) fields.hidden = false;
            fillSlide("geo");
            setStatus(data.display ? `Position : ${data.display}` : "Position enregistrée.", false);
          } catch {
            setStatus("Position lue, mais l’adresse n’a pas pu être précisée.", true);
          }
        },
        () => showErrors({ geo: "Autorisez la localisation pour continuer, ou passez cette étape." }),
        { enableHighAccuracy: true, timeout: 12000 },
      );
    });

    wizard.querySelector("[data-notif-enable]")?.addEventListener("click", async () => {
      const btn = wizard.querySelector("[data-notif-enable]");
      const state = wizard.querySelector("[data-notif-state]");
      if (btn) btn.disabled = true;
      if (state) state.textContent = "";
      try {
        if (typeof window.timaloveEnablePush !== "function") {
          throw new Error("Module notifications indisponible.");
        }
        const result = await window.timaloveEnablePush({ skipRegisterOnFailure: true });
        if (result.permission !== "granted") {
          throw new Error("Autorisation refusée.");
        }
        draft.fcm_token = result.token || "";
        draft.notifications_push = true;
        saveDraft(draft);
        if (state) state.textContent = "Notifications activées.";
        window.timaloveNotifPopup?.showSuccess(
          "Vous recevrez les likes, matchs et messages en temps réel.",
        );
        if (draft.channel === "oauth" && result.token) {
          await fetch("/api/push/register/", {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
            body: JSON.stringify({ token: result.token, platform: "web" }),
          }).catch(() => {});
        }
      } catch (err) {
        if (state) state.textContent = err.message || "Activation impossible pour le moment.";
        window.timaloveNotifPopup?.showError(
          err.message || "Activez les notifications dans les paramètres du navigateur.",
        );
      } finally {
        if (btn) btn.disabled = false;
      }
    });

    const params = new URLSearchParams(window.location.search);
    const oauthIncomplete = panel.getAttribute("data-oauth-incomplete") === "true";
    const prefill = readPrefill();
    if (oauthIncomplete) {
      startOauth(Object.assign({}, prefill, { channel: "oauth" }));
    } else if (panel.getAttribute("data-open-signup") === "true" || params.get("signup") === "1") {
      api.showChoice();
    }
  });
})();
