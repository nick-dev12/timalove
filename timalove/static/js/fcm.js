/**
 * TimaLove — enregistrement FCM token (utilisateurs connectés).
 */
(function () {
  const TOKEN_KEY = "timalove_fcm_token";
  const FIREBASE_VERSION = "12.18.0";

  function normalizeNotifUrl(url) {
    const origin = window.location.origin;
    const fallback = origin + "/";
    if (!url || typeof url !== "string") return fallback;

    let raw = url.trim();
    // SITE_URL mal configuré (ex. https://a.com,https://www.a.com/discussions/…)
    if (raw.includes(",")) {
      const parts = raw.split(",");
      const withPath =
        parts.find(function (p) {
          return /\/discussions\/|\/likes\/|\/profil/.test(p);
        }) || parts[parts.length - 1];
      raw = (withPath || raw).trim();
    }

    if (raw.startsWith("/")) return origin + raw;

    try {
      const fixed = raw.replace(/^https\/\//i, "https://").replace(/^http\/\//i, "http://");
      const parsed = new URL(fixed, origin);
      if (parsed.hostname === "127.0.0.1" || parsed.hostname === "localhost") {
        return origin + parsed.pathname + parsed.search + parsed.hash;
      }
      if (parsed.hostname === window.location.hostname) {
        return parsed.href;
      }
      return parsed.href;
    } catch (_err) {
      const pathMatch =
        raw.match(/(\/discussions\/[^?\s#,]+)/) ||
        raw.match(/(\/likes\/?[^?\s#,]*)/) ||
        raw.match(/(\/profil[^?\s#,]*)/);
      if (pathMatch) return origin + pathMatch[1];
      return raw.startsWith("/") ? origin + raw : fallback;
    }
  }

  window.timaloveNormalizeNotifUrl = normalizeNotifUrl;

  function isTestPush(data) {
    return data && (data.test === "true" || data.test === true);
  }

  function showOsNotification(options) {
    const opts = options || {};
    if (!("Notification" in window) || Notification.permission !== "granted") {
      return false;
    }
    if (!opts.force && document.visibilityState === "visible") {
      return false;
    }
    const title = opts.title || "TimaLove";
    const body = opts.body || opts.message || "";
    const url = normalizeNotifUrl(opts.url || "/");
    const tag = opts.tag || "timalove-" + (opts.type || "notif") + "-" + Date.now();
    const icon = opts.icon || "/static/images/logo.webp";
    try {
      const n = new Notification(title, {
        body: body,
        icon: icon,
        tag: tag,
        data: { url: url },
      });
      n.onclick = function () {
        window.focus();
        if (url) window.location.href = url;
        n.close();
      };
      if (navigator.serviceWorker) {
        navigator.serviceWorker.ready
          .then(function (reg) {
            return reg.showNotification(title, {
              body: body,
              icon: icon,
              tag: tag,
              renotify: true,
              data: { url: url },
            });
          })
          .catch(function () {});
      }
      return true;
    } catch (_err) {
      return false;
    }
  }

  window.timaloveShowOsNotification = showOsNotification;

  function getCookie(name) {
    const match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[1]) : "";
  }

  async function registerToken(token) {
    const res = await fetch("/api/push/register/", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({ token, platform: "web" }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.message || "Enregistrement du token push impossible.");
    }
    try {
      sessionStorage.setItem(TOKEN_KEY, token);
    } catch (_e) {
      /* ignore */
    }
    return token;
  }

  async function requestPermissionAndToken(config) {
    let permission = Notification.permission;
    if (permission === "default") {
      permission = await Notification.requestPermission();
    }
    if (permission !== "granted") {
      throw new Error("Autorisation refusée. Activez les notifications dans les paramètres du navigateur.");
    }

    if (!config.enabled || !config.firebase?.apiKey) {
      return { permission: "granted", token: null, fcmEnabled: false };
    }

    const token = await obtainToken(config);
    return { permission: "granted", token, fcmEnabled: true };
  }

  async function unregisterStoredToken() {
    let token = "";
    try {
      token = sessionStorage.getItem(TOKEN_KEY) || "";
    } catch (_e) {
      /* ignore */
    }
    if (!token) return;
    await fetch("/api/push/unregister/", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({ token }),
    });
    try {
      sessionStorage.removeItem(TOKEN_KEY);
    } catch (_e) {
      /* ignore */
    }
  }

  async function fetchPushConfig() {
    const configRes = await fetch("/api/push/config/");
    if (!configRes.ok) {
      throw new Error("Configuration push indisponible.");
    }
    return configRes.json();
  }

  async function obtainToken(config) {
    const { initializeApp } = await import(
      `https://www.gstatic.com/firebasejs/${FIREBASE_VERSION}/firebase-app.js`
    );
    const { getMessaging, getToken, onMessage, isSupported } = await import(
      `https://www.gstatic.com/firebasejs/${FIREBASE_VERSION}/firebase-messaging.js`
    );

    if (!(await isSupported())) {
      throw new Error("Les notifications push ne sont pas prises en charge sur cet appareil.");
    }

    const app = initializeApp(config.firebase);
    const messaging = getMessaging(app);

    const registration = await navigator.serviceWorker.register("/firebase-messaging-sw.js", {
      updateViaCache: "none",
    });
    await registration.update().catch(function () {});
    await navigator.serviceWorker.ready;

    const token = await getToken(messaging, {
      vapidKey: config.vapidKey,
      serviceWorkerRegistration: registration,
    });

    if (!token) {
      throw new Error("Impossible d’obtenir le token de notification.");
    }

    onMessage(messaging, function (payload) {
      const data = (payload && payload.data) || {};
      const title = (payload.notification && payload.notification.title) || data.title || "TimaLove";
      const body = (payload.notification && payload.notification.body) || data.message || "";
      const url = normalizeNotifUrl(data.url || "/");
      document.dispatchEvent(
        new CustomEvent("timalove:fcm", {
          detail: {
            id: data.notification_id || "",
            type: data.type || "",
            kind: data.type || "",
            title: title,
            message: body,
            url: url,
            related_user_id: data.related_user_id || null,
            test: data.test === "true" || data.test === true,
          },
        })
      );
      const forceOs = isTestPush(data);
      if (!forceOs && document.visibilityState === "visible") return;
      showOsNotification({
        title: title,
        body: body,
        url: url,
        type: data.type || "notif",
        tag: forceOs
          ? "timalove-test"
          : "timalove-" + (data.type || "notif") + "-" + (data.notification_id || Date.now()),
        force: forceOs,
      });
    });

    return token;
  }

  async function enablePush(options) {
    const opts = options || {};
    if (!("Notification" in window) || !("serviceWorker" in navigator)) {
      throw new Error("Votre navigateur ne prend pas en charge les notifications.");
    }

    const config = await fetchPushConfig();
    const result = await requestPermissionAndToken(config);

    if (result.token && opts.register !== false) {
      try {
        await registerToken(result.token);
        result.registered = true;
      } catch (err) {
        if (opts.skipRegisterOnFailure) {
          result.registered = false;
          result.registerError = err.message;
        } else {
          throw err;
        }
      }
    }

    return result;
  }

  async function disablePush() {
    await unregisterStoredToken();
  }

  async function initFCM() {
    if (!("Notification" in window) || !("serviceWorker" in navigator)) {
      return;
    }
    if (Notification.permission !== "granted") {
      return;
    }

    try {
      const config = await fetchPushConfig();
      if (!config.enabled || !config.firebase?.apiKey) return;
      const token = await obtainToken(config);
      if (token) await registerToken(token);
    } catch (err) {
      console.warn("[fcm]", err);
    }
  }

  window.timaloveEnablePush = enablePush;
  window.timaloveDisablePush = disablePush;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      initFCM().catch((err) => console.warn("[fcm]", err));
    });
  } else {
    initFCM().catch((err) => console.warn("[fcm]", err));
  }
})();
