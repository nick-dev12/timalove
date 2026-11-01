/**
 * TimaLove — PWA : enregistrement du service worker, popup d'installation et bouton « Télécharger ».
 *
 * - PC / Android (Chrome, Edge, Samsung…) : « Installer » déclenche directement l'installation native.
 * - iPhone / iPad et navigateurs sans installation native : « Installer » affiche la méthode pas à pas.
 * - Dans l'application installée : ni popup ni bouton.
 *
 * Aperçu forcé (tests) : ?pwa_preview=native|ios-safari|ios-chrome|ios-firefox|ios-inapp|
 *                        android-manual|android-firefox|android-inapp|mac-safari
 * Bouton de navigation : tout élément [data-pwa-install] (masqué tant que l'installation est impossible).
 */
(function () {
  const SW_URL = "/firebase-messaging-sw.js";
  const DISMISS_KEY = "timalove_pwa_dismissed_at";
  const SESSION_KEY = "timalove_pwa_shown";
  const DISMISS_DAYS = 7;
  const SHOW_DELAY_MS = 4000;
  const MANUAL_FALLBACK_MS = 3500;

  let deferredPrompt = null;
  let mode = null;
  let sheet = null;

  /* ---------- Stockage tolérant (navigation privée, etc.) ---------- */
  function storeGet(store, key) {
    try { return window[store].getItem(key); } catch (_e) { return null; }
  }
  function storeSet(store, key, value) {
    try { window[store].setItem(key, value); } catch (_e) { /* ignore */ }
  }

  /* ---------- Détection ---------- */
  const ua = navigator.userAgent || "";
  const isIOS = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  const isIPad = /iPad/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  const isAndroid = /Android/i.test(ua);
  const isInApp = /FBAN|FBAV|FB_IAB|Instagram|TikTok|musical_ly|Snapchat|Line\/|Twitter|LinkedInApp|Pinterest|GSA\/|; wv\)/i.test(ua);
  const isMacSafari = !isIOS && /Macintosh/.test(ua) && /Safari/.test(ua) && !/Chrome|Chromium|Edg\/|Firefox|OPR/.test(ua);

  function isStandalone() {
    return (
      window.matchMedia("(display-mode: standalone)").matches ||
      window.matchMedia("(display-mode: minimal-ui)").matches ||
      window.navigator.standalone === true
    );
  }

  function detectManualMode() {
    if (isIOS) {
      if (isInApp) return "ios-inapp";
      if (/CriOS|EdgiOS|OPiOS/.test(ua)) return "ios-chrome";
      if (/FxiOS/.test(ua)) return "ios-firefox";
      return "ios-safari";
    }
    if (isAndroid) {
      if (isInApp) return "android-inapp";
      if (/Firefox/.test(ua)) return "android-firefox";
      return "android-manual";
    }
    if (isMacSafari) return "mac-safari";
    return null;
  }

  /* ---------- Icônes ---------- */
  const SHARE_ICON =
    '<svg class="pwa-ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v12M8 7l4-4 4 4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M7 10H5.5A1.5 1.5 0 0 0 4 11.5v8A1.5 1.5 0 0 0 5.5 21h13a1.5 1.5 0 0 0 1.5-1.5v-8a1.5 1.5 0 0 0-1.5-1.5H17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
  const ADD_ICON =
    '<svg class="pwa-ico" viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="4" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 8v8M8 12h8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
  const DOWNLOAD_ICON =
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v11M7.5 10.5 12 15l4.5-4.5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/><path d="M5 19h14" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>';
  const CLOSE_ICON =
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 7l10 10M17 7L7 17" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
  const ARROW_ICON =
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v15M6 13l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const DOTS_V = '<span class="pwa-key">⋮</span>';
  const DOTS_H = '<span class="pwa-key">•••</span>';

  /* ---------- Méthode d'installation par appareil ---------- */
  function guide(m) {
    const where = isIPad ? "en haut" : "en bas de l’écran";
    switch (m) {
      case "ios-safari":
        return {
          title: "Installer sur iPhone",
          steps: [
            "Touchez " + SHARE_ICON + " <strong>Partager</strong> " + where,
            "Choisissez <strong>Sur l’écran d’accueil</strong> " + ADD_ICON,
            "Touchez <strong>Ajouter</strong>",
          ],
          arrow: !isIPad,
        };
      case "ios-chrome":
        return {
          title: "Installer sur iPhone",
          steps: [
            "Touchez " + SHARE_ICON + " dans la barre d’adresse",
            "Choisissez <strong>Sur l’écran d’accueil</strong> " + ADD_ICON,
            "Touchez <strong>Ajouter</strong>",
          ],
          note: "Option absente ? Ouvrez le site dans Safari.",
        };
      case "ios-firefox":
        return {
          title: "Installer sur iPhone",
          steps: [
            "Touchez le menu ☰ puis " + SHARE_ICON + " <strong>Partager</strong>",
            "Choisissez <strong>Sur l’écran d’accueil</strong> " + ADD_ICON,
            "Touchez <strong>Ajouter</strong>",
          ],
          note: "Option absente ? Ouvrez le site dans Safari.",
        };
      case "ios-inapp":
        return {
          title: "Ouvrez dans Safari",
          steps: [
            "Touchez " + DOTS_H + " ou " + SHARE_ICON + " en haut ou en bas",
            "Choisissez <strong>Ouvrir dans Safari</strong>",
            "Puis touchez <strong>Installer</strong>",
          ],
          copy: true,
        };
      case "android-inapp":
        return {
          title: "Ouvrez dans Chrome",
          steps: [
            "Touchez le menu " + DOTS_V,
            "Choisissez <strong>Ouvrir dans Chrome</strong>",
            "Puis touchez <strong>Installer</strong>",
          ],
          copy: true,
        };
      case "android-firefox":
      case "android-manual":
        return {
          title: "Installer sur Android",
          steps: [
            "Touchez le menu " + DOTS_V + " du navigateur",
            "Choisissez <strong>Installer l’application</strong> ou <strong>Ajouter à l’écran d’accueil</strong>",
            "Confirmez avec <strong>Installer</strong>",
          ],
        };
      case "desktop":
        return {
          title: "Installer sur ordinateur",
          steps: [
            "Cliquez sur l’icône d’installation " + DOWNLOAD_ICON.replace("<svg", '<svg class="pwa-ico"') + " à droite de la barre d’adresse",
            "Ou ouvrez le menu " + DOTS_V + " puis <strong>Installer TimaLove</strong>",
            "Confirmez avec <strong>Installer</strong>",
          ],
        };
      case "mac-safari":
        return {
          title: "Installer sur Mac",
          steps: [
            "Ouvrez le menu <strong>Fichier</strong> (ou " + SHARE_ICON + ")",
            "Choisissez <strong>Ajouter au Dock</strong>",
            "Confirmez avec <strong>Ajouter</strong>",
          ],
        };
      default:
        return null;
    }
  }

  function isKnownMode(m) {
    return m === "native" || !!guide(m);
  }

  /* ---------- Popup ---------- */
  function iconUrl() {
    const link = document.querySelector('link[rel="apple-touch-icon"]');
    return link ? link.href : "/static/images/pwa/apple-touch-icon.png";
  }

  function promoHtml() {
    return (
      '<div class="pwa-row">' +
      '<img class="pwa-app-icon" src="' + iconUrl() + '" alt="" width="52" height="52">' +
      '<div class="pwa-text">' +
      '<h2 id="pwa-title">Profitez pleinement de TimaLove</h2>' +
      '<p>Une expérience plus fluide, plus rapide et toujours à portée de main.</p>' +
      "</div></div>" +
      '<button type="button" class="pwa-btn" data-pwa-action="install">' + DOWNLOAD_ICON + "<span>Installer l’application</span></button>"
    );
  }

  function guideHtml(g) {
    const steps = g.steps.map(function (s) { return "<li>" + s + "</li>"; }).join("");
    return (
      '<div class="pwa-row">' +
      '<img class="pwa-app-icon" src="' + iconUrl() + '" alt="" width="52" height="52">' +
      '<div class="pwa-text"><h2 id="pwa-title">' + g.title + "</h2><p>C’est gratuit et ça prend 10 secondes.</p></div>" +
      "</div>" +
      '<ol class="pwa-steps">' + steps + "</ol>" +
      (g.note ? '<p class="pwa-note">' + g.note + "</p>" : "") +
      (g.copy
        ? '<button type="button" class="pwa-btn" data-pwa-action="copy"><span>Copier le lien du site</span></button>'
        : '<button type="button" class="pwa-btn pwa-btn--soft" data-pwa-action="later"><span>J’ai compris</span></button>')
    );
  }

  function close(remember) {
    if (!sheet) return;
    if (remember) storeSet("localStorage", DISMISS_KEY, String(Date.now()));
    const node = sheet;
    sheet = null;
    node.classList.remove("is-open");
    document.removeEventListener("keydown", onKey);
    setTimeout(function () { node.remove(); }, 260);
  }

  function onKey(e) {
    if (e.key === "Escape") close(true);
  }

  function open(view) {
    if (!mode || isStandalone()) return false;
    const g = mode === "native" ? null : guide(mode);
    const showGuide = view === "guide" && g;

    if (!sheet) {
      sheet = document.createElement("div");
      sheet.className = "pwa-sheet";
      sheet.innerHTML =
        '<div class="pwa-backdrop" data-pwa-action="later"></div>' +
        '<div class="pwa-card" role="dialog" aria-modal="false" aria-labelledby="pwa-title">' +
        '<button type="button" class="pwa-close" data-pwa-action="later" aria-label="Fermer">' + CLOSE_ICON + "</button>" +
        '<div class="pwa-content"></div></div>' +
        '<div class="pwa-arrow" aria-hidden="true">' + ARROW_ICON + "</div>";
      sheet.addEventListener("click", onSheetClick);
      document.addEventListener("keydown", onKey);
      document.body.appendChild(sheet);
      void sheet.offsetWidth; // force le reflow pour déclencher la transition
      sheet.classList.add("is-open");
      storeSet("sessionStorage", SESSION_KEY, "1");
    }
    sheet.setAttribute("data-pwa-mode", mode);
    sheet.classList.toggle("is-guide", !!showGuide);
    sheet.classList.toggle("has-arrow", !!(showGuide && g.arrow));
    sheet.querySelector(".pwa-content").innerHTML = showGuide ? guideHtml(g) : promoHtml();
    const focusable = sheet.querySelector(".pwa-btn");
    if (focusable) focusable.focus({ preventScroll: true });
    return true;
  }

  function onSheetClick(e) {
    const el = e.target.closest("[data-pwa-action]");
    if (!el) return;
    const action = el.getAttribute("data-pwa-action");
    if (action === "install") install();
    else if (action === "copy") copyLink(el);
    else close(true);
  }

  /** Bouton « Installer » : installation native si possible, sinon la méthode pas à pas. */
  async function install() {
    if (mode === "native" && deferredPrompt) {
      const promptEvent = deferredPrompt;
      deferredPrompt = null;
      promptEvent.prompt();
      let outcome = "dismissed";
      try {
        const choice = await promptEvent.userChoice;
        outcome = choice && choice.outcome;
      } catch (_e) { /* ignore */ }
      close(outcome !== "accepted");
      return;
    }
    if (mode === "native") {
      // L'évènement natif a déjà été consommé : Chrome ne le rendra qu'au prochain chargement.
      mode = detectManualMode() || (isAndroid ? "android-manual" : "desktop");
    }
    open("guide");
  }

  function copyLink(btn) {
    const url = window.location.origin + "/";
    const label = btn.querySelector("span") || btn;
    const done = function () { label.textContent = "Lien copié ✓"; };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(done, function () { window.prompt("Copiez ce lien :", url); });
    } else {
      window.prompt("Copiez ce lien :", url);
    }
  }

  /* ---------- Affichage automatique ---------- */
  function recentlyDismissed() {
    const at = parseInt(storeGet("localStorage", DISMISS_KEY) || "0", 10);
    return at && Date.now() - at < DISMISS_DAYS * 86400000;
  }

  function otherModalVisible() {
    const nodes = document.querySelectorAll("dialog[open], [aria-modal='true']");
    for (let i = 0; i < nodes.length; i++) {
      if (!nodes[i].closest(".pwa-sheet") && nodes[i].getClientRects().length) return true;
    }
    return false;
  }

  function autoShow(attempt) {
    if (isStandalone() || !mode) return;
    if (recentlyDismissed() || storeGet("sessionStorage", SESSION_KEY)) return;
    if (/^\/(espace-prive|hors-ligne)/.test(location.pathname)) return;
    setTimeout(function () {
      if (sheet || !mode || recentlyDismissed()) return;
      // Ne pas empiler sur un autre popup (genre, projet, filtres…) : on réessaie plus tard.
      if (otherModalVisible()) {
        if ((attempt || 0) < 6) autoShow((attempt || 0) + 1);
        return;
      }
      open("promo");
    }, SHOW_DELAY_MS);
  }

  function syncButtons() {
    const show = !isStandalone() && !!mode;
    document.documentElement.classList.toggle("pwa-can-install", show);
    document.querySelectorAll("[data-pwa-install]").forEach(function (el) {
      el.hidden = !show;
    });
  }

  async function alreadyInstalled() {
    if (!navigator.getInstalledRelatedApps) return false;
    try {
      const apps = await navigator.getInstalledRelatedApps();
      return apps.length > 0;
    } catch (_e) {
      return false;
    }
  }

  /* ---------- Service worker ---------- */
  function registerServiceWorker() {
    if (!("serviceWorker" in navigator) || !window.isSecureContext) return;
    navigator.serviceWorker
      .register(SW_URL, { scope: "/", updateViaCache: "none" })
      .catch(function (err) { console.warn("[TimaLove PWA] service worker:", err); });
  }

  /* ---------- Initialisation ---------- */
  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferredPrompt = e;
    const firstTime = mode === null;
    mode = "native";
    syncButtons();
    if (sheet && sheet.classList.contains("is-guide")) open("promo");
    else if (firstTime) autoShow();
  });

  window.addEventListener("appinstalled", function () {
    deferredPrompt = null;
    mode = null;
    close(false);
    syncButtons();
  });

  // Bouton « Télécharger » de la navigation : installe directement (PC / Android) ou montre la méthode.
  document.addEventListener("click", function (e) {
    const btn = e.target.closest("[data-pwa-install]");
    if (!btn) return;
    e.preventDefault();
    if (mode) install();
  });

  // Passage en mode application (ex. ouverture depuis l'icône) : tout masquer.
  window.matchMedia("(display-mode: standalone)").addEventListener("change", function () {
    if (isStandalone()) { close(false); syncButtons(); }
  });

  window.TimaLovePWA = {
    open: function () { return open("promo"); },
    install: install,
    get mode() { return mode; },
    isStandalone: isStandalone,
  };

  function init() {
    registerServiceWorker();
    if (isStandalone()) {
      syncButtons();
      return;
    }
    const preview = new URLSearchParams(location.search).get("pwa_preview");
    if (preview && isKnownMode(preview)) {
      mode = preview;
      syncButtons();
      setTimeout(function () { open("promo"); }, 300);
      return;
    }
    // iOS / Firefox / navigateurs intégrés : pas de beforeinstallprompt → méthode manuelle.
    const manual = detectManualMode();
    const delay = isIOS || isMacSafari ? 0 : MANUAL_FALLBACK_MS;
    setTimeout(async function () {
      if (mode || !manual) return;
      if (await alreadyInstalled()) return;
      mode = manual;
      syncButtons();
      autoShow();
    }, delay);
    syncButtons();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
