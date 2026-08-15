/**
 * TimaLove — connexion Google / Apple (Firebase Auth) + onglets téléphone / email.
 */
(function () {
  function getCookie(name) {
    const match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[1]) : "";
  }

  function readConfig() {
    const node = document.getElementById("firebase-web-config");
    if (!node) return null;
    try {
      return JSON.parse(node.textContent || "{}");
    } catch {
      return null;
    }
  }

  function setStatus(el, message, isError) {
    if (!el) return;
    el.hidden = !message;
    el.textContent = message || "";
    el.classList.toggle("is-error", Boolean(isError));
  }

  document.addEventListener("DOMContentLoaded", () => {
    const panel = document.querySelector("[data-auth-panel]");
    const form = document.querySelector("[data-auth-form]");
    const statusEl = document.querySelector("[data-auth-status]");
    const modeInput = document.querySelector("[data-auth-mode]");
    const phoneInput = document.getElementById("auth-phone");
    const emailInput = document.getElementById("auth-email");
    const phoneHidden = document.querySelector("[data-auth-phone-e164]");
    const params = new URLSearchParams(window.location.search);
    const nextUrl = params.get("next") || sessionStorage.getItem("tl_next") || "";
    let iti = null;
    let busy = false;

    function currentMode() {
      return modeInput?.value === "email" ? "email" : "phone";
    }

    function setTab(mode) {
      const next = mode === "email" ? "email" : "phone";
      if (modeInput) modeInput.value = next;
      document.querySelectorAll("[data-auth-tab]").forEach((tab) => {
        const on = tab.getAttribute("data-auth-tab") === next;
        tab.classList.toggle("is-active", on);
        tab.setAttribute("aria-selected", on ? "true" : "false");
      });
      document.querySelectorAll("[data-auth-pane]").forEach((pane) => {
        const on = pane.getAttribute("data-auth-pane") === next;
        pane.classList.toggle("is-hidden", !on);
      });
      if (phoneInput) phoneInput.required = next === "phone";
      if (emailInput) emailInput.required = next === "email";
      if (next === "phone") phoneInput?.focus();
      else emailInput?.focus();
    }

    document.querySelectorAll("[data-auth-tab]").forEach((tab) => {
      tab.addEventListener("click", () => setTab(tab.getAttribute("data-auth-tab")));
    });

    const initialMode = panel?.getAttribute("data-login-mode") || "phone";
    setTab(initialMode);

    if (phoneInput && window.intlTelInput) {
      iti = window.intlTelInput(phoneInput, {
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
    }

    form?.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (busy) return;
      if (currentMode() === "phone") {
        if (iti) {
          const utilsReady = typeof window.intlTelInputUtils !== "undefined";
          if (
            utilsReady &&
            phoneInput.value.trim() &&
            typeof iti.isValidNumber === "function" &&
            !iti.isValidNumber()
          ) {
            setStatus(statusEl, "Indiquez un numéro de téléphone valide.", true);
            phoneInput.focus();
            return;
          }
          if (phoneHidden) phoneHidden.value = iti.getNumber() || phoneInput.value;
        } else if (phoneHidden) {
          phoneHidden.value = phoneInput?.value || "";
        }
      }
      busy = true;
      setStatus(statusEl, "Connexion en cours…", false);
      try {
        const payload = new FormData(form);
        if (currentMode() === "email") payload.delete("phone");
        else payload.delete("email");
        const res = await fetch(form.action, {
          method: "POST",
          body: payload,
          credentials: "same-origin",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            Accept: "application/json",
          },
        });
        let data = {};
        try {
          data = await res.json();
        } catch {
          data = {};
        }
        if (res.ok && data.ok) {
          const href = data.redirect || "/explorer/";
          if (window.TimaLoveTransit?.start) window.TimaLoveTransit.start(href);
          else window.location.href = href;
          return;
        }
        setStatus(statusEl, data.message || "Identifiants incorrects.", true);
      } catch (err) {
        setStatus(statusEl, err.message || "Connexion interrompue. Réessayez.", true);
      } finally {
        busy = false;
      }
    });

    async function sendToken(idToken, provider) {
      const endpoint = provider === "apple" ? "/api/auth/apple/" : "/api/auth/google/";
      const res = await fetch(endpoint, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({ idToken, next: nextUrl }),
      });
      let data = {};
      try {
        data = await res.json();
      } catch {
        data = {};
      }
      if (!res.ok || !data.ok) {
        throw new Error(data.message || "Connexion refusée.");
      }
      sessionStorage.removeItem("tl_next");
      if (data.needs_completion && window.TimaLoveSignup?.startOauth) {
        window.TimaLoveSignup.startOauth(data.profile || {});
        setStatus(statusEl, "", false);
        setSocialBusy(false);
        return;
      }
      if (window.TimaLoveTransit?.start) {
        window.TimaLoveTransit.start(data.redirect || "/explorer/");
      } else {
        window.location.href = data.redirect || "/explorer/";
      }
    }

    async function loadFirebase() {
      const config = readConfig();
      if (!config?.apiKey) {
        throw new Error("Connexion sociale non configurée.");
      }
      const { initializeApp, getApps } = await import(
        "https://www.gstatic.com/firebasejs/12.17.1/firebase-app.js"
      );
      const authMod = await import("https://www.gstatic.com/firebasejs/12.17.1/firebase-auth.js");
      const app = getApps().length ? getApps()[0] : initializeApp(config);
      const auth = authMod.getAuth(app);
      return { auth, ...authMod };
    }

    function setSocialBusy(isBusy) {
      busy = isBusy;
      document.querySelectorAll("[data-auth-google], [data-auth-apple]").forEach((btn) => {
        btn.disabled = isBusy;
      });
    }

    async function finishWithUser(user, provider) {
      setStatus(statusEl, "Connexion en cours…", false);
      const idToken = await user.getIdToken();
      await sendToken(idToken, provider);
    }

    async function signInWithProvider(kind) {
      if (busy) return;
      const isApple = kind === "apple";
      const label = isApple ? "Apple" : "Google";
      setSocialBusy(true);
      setStatus(statusEl, `Ouverture de ${label}…`, false);
      if (nextUrl) sessionStorage.setItem("tl_next", nextUrl);

      try {
        const {
          auth,
          GoogleAuthProvider,
          OAuthProvider,
          signInWithPopup,
          signInWithRedirect,
        } = await loadFirebase();
        const provider = isApple ? new OAuthProvider("apple.com") : new GoogleAuthProvider();
        provider.addScope("email");
        if (isApple) provider.addScope("name");
        else {
          provider.addScope("profile");
          provider.setCustomParameters({ prompt: "select_account" });
        }

        try {
          const result = await signInWithPopup(auth, provider);
          await finishWithUser(result.user, kind);
          return;
        } catch (popupErr) {
          const code = popupErr?.code || "";
          if (code === "auth/popup-closed-by-user" || code === "auth/cancelled-popup-request") {
            setStatus(statusEl, "", false);
            setSocialBusy(false);
            return;
          }
          if (code === "auth/operation-not-allowed") {
            setStatus(
              statusEl,
              `${label} n’est pas encore activé dans Firebase Authentication.`,
              true,
            );
            setSocialBusy(false);
            return;
          }
          setStatus(statusEl, `Redirection vers ${label}…`, false);
          sessionStorage.setItem("tl_oauth_provider", kind);
          await signInWithRedirect(auth, provider);
        }
      } catch (err) {
        const code = err?.code || "";
        if (code === "auth/unauthorized-domain") {
          setStatus(
            statusEl,
            "Ajoutez 127.0.0.1 dans Firebase → Authentication → Settings → Authorized domains.",
            true,
          );
        } else {
          setStatus(statusEl, err.message || `Connexion ${label} interrompue. Réessayez.`, true);
        }
        setSocialBusy(false);
      }
    }

    async function recoverRedirect() {
      try {
        const { auth, getRedirectResult } = await loadFirebase();
        const result = await getRedirectResult(auth);
        if (!result?.user) return;
        const kind = sessionStorage.getItem("tl_oauth_provider") || "google";
        sessionStorage.removeItem("tl_oauth_provider");
        setSocialBusy(true);
        await finishWithUser(result.user, kind);
      } catch (err) {
        setStatus(statusEl, err.message || "Connexion sociale interrompue.", true);
        setSocialBusy(false);
      }
    }

    document.addEventListener("click", (event) => {
      const googleBtn = event.target.closest("[data-auth-google]");
      const appleBtn = event.target.closest("[data-auth-apple]");
      if (googleBtn) {
        event.preventDefault();
        void signInWithProvider("google");
      }
      if (appleBtn) {
        event.preventDefault();
        void signInWithProvider("apple");
      }
    });

    void recoverRedirect().then(() => {
      if (params.get("via") === "google") void signInWithProvider("google");
      if (params.get("via") === "apple") void signInWithProvider("apple");
    });
  });
})();
