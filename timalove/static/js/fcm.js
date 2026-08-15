/**
 * TimaLove — enregistrement FCM token (utilisateurs connectés).
 */
(function () {
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
      console.warn("[fcm] enregistrement token échoué", res.status);
    }
  }

  async function initFCM() {
    if (!("Notification" in window) || !("serviceWorker" in navigator)) {
      return;
    }

    const configRes = await fetch("/api/push/config/");
    if (!configRes.ok) return;

    const config = await configRes.json();
    if (!config.enabled || !config.firebase?.apiKey) return;

    const { initializeApp } = await import(
      "https://www.gstatic.com/firebasejs/12.17.1/firebase-app.js"
    );
    const { getMessaging, getToken, onMessage, isSupported } = await import(
      "https://www.gstatic.com/firebasejs/12.17.1/firebase-messaging.js"
    );

    if (!(await isSupported())) return;

    const app = initializeApp(config.firebase);
    const messaging = getMessaging(app);

    const registration = await navigator.serviceWorker.register("/firebase-messaging-sw.js");
    await navigator.serviceWorker.ready;

    let permission = Notification.permission;
    if (permission === "default") {
      permission = await Notification.requestPermission();
    }
    if (permission !== "granted") return;

    const token = await getToken(messaging, {
      vapidKey: config.vapidKey,
      serviceWorkerRegistration: registration,
    });

    if (token) {
      await registerToken(token);
    }

    onMessage(messaging, (payload) => {
      const title = payload.notification?.title || "TimaLove";
      const body = payload.notification?.body || "";
      if (document.visibilityState === "visible" && Notification.permission === "granted") {
        new Notification(title, {
          body,
          icon: "/static/images/logo.webp",
          data: payload.data || {},
        });
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      initFCM().catch((err) => console.warn("[fcm]", err));
    });
  } else {
    initFCM().catch((err) => console.warn("[fcm]", err));
  }
})();
