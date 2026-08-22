/**
 * TimaLove — notifications temps réel (messages, likes, super likes, matchs).
 * Connexion WS persistante : reste ouverte même si l’onglet n’est plus au premier plan.
 */
(function () {
  if (window.timaloveRealtime) return;
  window.timaloveRealtime = true;
  if (document.body && document.body.classList.contains("is-guest")) return;

  const POPUP_MS = 7000;
  const PING_MS = 25000;
  const POLL_MS = 20000;
  const SEEN_MAX = 40;

  let ws = null;
  let retryTimer = null;
  let pingTimer = null;
  let retryDelay = 2000;
  let popupTimer = null;
  const seenIds = [];

  function notificationsUrl() {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return proto + "//" + window.location.host + "/ws/notifications/";
  }

  function currentPartnerId() {
    const section = document.querySelector(".msg[data-partner-id]");
    return section ? section.getAttribute("data-partner-id") : "";
  }

  function onSameThread(partnerId) {
    return (
      document.body.classList.contains("messages-page") &&
      partnerId &&
      currentPartnerId() === String(partnerId)
    );
  }

  function alreadySeen(id) {
    if (!id) return false;
    if (seenIds.indexOf(id) !== -1) return true;
    seenIds.push(id);
    if (seenIds.length > SEEN_MAX) seenIds.shift();
    return false;
  }

  function renderBadge(selector, count, tabSelector, label) {
    const badge = document.querySelector(selector);
    const tab = document.querySelector(tabSelector);
    if (!badge) return;
    const n = Math.max(0, parseInt(count, 10) || 0);
    badge.hidden = n < 1;
    badge.textContent = n > 99 ? "99+" : String(n);
    if (!tab) return;
    if (n > 0) {
      tab.setAttribute("aria-label", label + ", " + n);
    } else if (tab.getAttribute("aria-current") === "page") {
      tab.setAttribute("aria-label", label);
    } else {
      tab.removeAttribute("aria-label");
    }
  }

  function renderUnreadMessages(count) {
    renderBadge("[data-unread-messages]", count, "[data-dock-messages]", "Messages");
  }

  function renderUnreadNotifications(count) {
    const badge = document.querySelector("[data-unread-notifications]");
    const bell = document.querySelector(".explorer__bell");
    if (!badge) return;
    const n = Math.max(0, parseInt(count, 10) || 0);
    badge.hidden = n < 1;
    badge.textContent = n > 99 ? "99+" : String(n);
    if (!bell) return;
    if (n > 0) {
      bell.setAttribute(
        "aria-label",
        "Notifications, " + n + (n > 1 ? " non lues" : " non lue")
      );
    } else {
      bell.setAttribute("aria-label", "Notifications");
    }
  }

  function renderLikesCount(count) {
    if (document.body.classList.contains("likes-page")) {
      renderBadge("[data-unread-likes]", 0, "[data-dock-likes]", "Likes");
      return;
    }
    renderBadge("[data-unread-likes]", count, "[data-dock-likes]", "Likes");
  }

  window.timaloveRenderUnreadBadge = renderUnreadMessages;
  window.timaloveRenderLikesBadge = renderLikesCount;
  window.timaloveRenderNotificationsBadge = renderUnreadNotifications;

  function fetchUnread() {
    fetch("/api/messages/unread-count/", {
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (res) {
        if (!res.ok) throw new Error("unread");
        return res.json();
      })
      .then(function (data) {
        renderUnreadMessages(data && data.count);
      })
      .catch(function () {});
  }

  function fetchLikesCount() {
    fetch("/api/likes/count/", {
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (res) {
        if (!res.ok) throw new Error("likes");
        return res.json();
      })
      .then(function (data) {
        renderLikesCount(data && data.count);
      })
      .catch(function () {});
  }

  function fetchNotificationsCount() {
    fetch("/api/notifications/unread-count/", {
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (res) {
        if (!res.ok) throw new Error("notifications");
        return res.json();
      })
      .then(function (data) {
        renderUnreadNotifications(data && data.count);
      })
      .catch(function () {});
  }

  window.timaloveRefreshUnreadBadge = fetchUnread;

  function normalizeNotifUrl(url) {
    if (typeof window.timaloveNormalizeNotifUrl === "function") {
      return window.timaloveNormalizeNotifUrl(url);
    }
    return url || "/";
  }

  function kindMeta(payload) {
    const kind = payload.kind || payload.type || "";
    if (kind === "new_match") {
      return { kicker: "C’est un match", cta: "Écrire", icon: "♥" };
    }
    if (kind === "super_like") {
      return { kicker: "Super like", cta: "Voir", icon: "★" };
    }
    if (kind === "new_like") {
      return { kicker: "Nouveau like", cta: "Voir", icon: "♡" };
    }
    return { kicker: "Nouveau message", cta: "Répondre", icon: "✉" };
  }

  function ensurePopup() {
    let root = document.getElementById("timalove-live-popup");
    if (root) return root;
    root = document.createElement("div");
    root.id = "timalove-live-popup";
    root.className = "live-popup";
    root.hidden = true;
    root.setAttribute("role", "status");
    root.setAttribute("aria-live", "polite");
    root.innerHTML =
      '<div class="live-popup__card" data-live-open>' +
      '<span class="live-popup__photo" data-live-photo aria-hidden="true"></span>' +
      '<span class="live-popup__copy">' +
      '<span class="live-popup__kicker" data-live-kicker></span>' +
      '<strong class="live-popup__title" data-live-title></strong>' +
      '<span class="live-popup__text" data-live-text></span>' +
      "</span>" +
      '<span class="live-popup__cta" data-live-cta>Voir</span>' +
      "</div>" +
      '<button type="button" class="live-popup__close" data-live-close aria-label="Fermer">×</button>';
    document.body.appendChild(root);
    root.querySelector("[data-live-close]").addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      hidePopup();
    });
    root.querySelector("[data-live-open]").addEventListener("click", function () {
      const url = root.getAttribute("data-url");
      hidePopup();
      if (url) window.location.href = url;
    });
    return root;
  }

  function hidePopup() {
    const root = document.getElementById("timalove-live-popup");
    if (!root) return;
    root.hidden = true;
    window.clearTimeout(popupTimer);
  }

  function showPopup(payload) {
    const root = ensurePopup();
    const meta = kindMeta(payload);
    const name = payload.related_user_name || payload.title || "TimaLove";
    const photoEl = root.querySelector("[data-live-photo]");
    if (payload.related_user_photo) {
      photoEl.innerHTML = '<img src="' + payload.related_user_photo + '" alt="">';
    } else {
      photoEl.innerHTML = "<span>" + (payload.related_user_initial || meta.icon) + "</span>";
    }
    root.querySelector("[data-live-kicker]").textContent = meta.kicker;
    root.querySelector("[data-live-title]").textContent = name;
    root.querySelector("[data-live-text]").textContent = payload.message || "";
    root.querySelector("[data-live-cta]").textContent = meta.cta;
    root.setAttribute("data-url", normalizeNotifUrl(payload.url || "/"));
    root.setAttribute("data-kind", payload.kind || payload.type || "");
    root.hidden = false;
    window.clearTimeout(popupTimer);
    popupTimer = window.setTimeout(hidePopup, POPUP_MS);
  }

  function isTestNotification(payload) {
    const kind = payload.kind || payload.type || "";
    return kind === "profile_approved" && (payload.test === true || payload.test === "true" || payload.title === "Test TimaLove");
  }

  function showNative(payload) {
    if (!("Notification" in window) || Notification.permission !== "granted") return;
    const forceOs = isTestNotification(payload);
    if (!forceOs && document.visibilityState === "visible") return;
    if (forceOs && window.timaloveShowOsNotification) {
      void window.timaloveShowOsNotification({
        title: payload.title || "TimaLove",
        body: payload.message || "",
        url: payload.url || "/",
        tag: "timalove-test",
        force: true,
      });
      return;
    }
    const title = payload.title || "TimaLove";
    const body = payload.message || "";
    const url = normalizeNotifUrl(payload.url || "/");
    const tag =
      "timalove-" + (payload.kind || payload.type || "notif") + "-" + (payload.related_user_id || payload.id || "");
    if (navigator.serviceWorker) {
      navigator.serviceWorker.ready
        .then(function (reg) {
          return reg.showNotification(title, {
            body: body,
            icon: payload.related_user_photo || "/static/images/logo.webp",
            tag: tag,
            renotify: true,
            data: { url: url },
          });
        })
        .catch(function () {});
      return;
    }
    try {
      const n = new Notification(title, {
        body: body,
        icon: payload.related_user_photo || "/static/images/logo.webp",
        tag: tag,
        data: { url: url },
      });
      n.onclick = function () {
        window.focus();
        if (url) window.location.href = url;
        n.close();
      };
    } catch (_err) {
      /* ignore */
    }
  }

  function handleNotification(payload) {
    if (!payload || payload.event === "pong") return;
    if (!payload.type && !payload.kind) return;
    if (alreadySeen(payload.id)) return;

    if (typeof payload.unread_messages === "number") {
      renderUnreadMessages(payload.unread_messages);
    } else {
      fetchUnread();
    }
    if (typeof payload.likes_count === "number") {
      renderLikesCount(payload.likes_count);
    }
    if (typeof payload.unread_notifications === "number") {
      renderUnreadNotifications(payload.unread_notifications);
    } else {
      fetchNotificationsCount();
    }

    const kind = payload.kind || payload.type || "";
    const partnerId = payload.related_user_id || "";

    if (kind === "new_message") {
      document.dispatchEvent(new CustomEvent("timalove:inbox-refresh", { detail: payload }));
      if (onSameThread(partnerId)) return;
    }
    if (kind === "new_like" || kind === "super_like" || kind === "new_match") {
      document.dispatchEvent(new CustomEvent("timalove:likes-refresh", { detail: payload }));
    }

    if (kind === "new_like" && document.body.classList.contains("likes-page")) {
      showNative(payload);
      return;
    }

    showPopup(payload);
    showNative(payload);
  }

  function stopPing() {
    window.clearInterval(pingTimer);
    pingTimer = null;
  }

  function startPing() {
    stopPing();
    pingTimer = window.setInterval(function () {
      if (ws && ws.readyState === WebSocket.OPEN) {
        try {
          ws.send(JSON.stringify({ type: "ping" }));
        } catch (_err) {
          /* ignore */
        }
      }
    }, PING_MS);
  }

  function connect() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      return;
    }
    ws = new WebSocket(notificationsUrl());

    ws.onopen = function () {
      retryDelay = 2000;
      startPing();
      fetchUnread();
      fetchLikesCount();
      fetchNotificationsCount();
    };

    ws.onmessage = function (event) {
      try {
        const payload = JSON.parse(event.data);
        if (payload && (payload.event === "connected" || payload.event === "pong")) return;
        handleNotification(payload);
      } catch (_err) {
        /* ignore */
      }
    };

    ws.onclose = function () {
      ws = null;
      stopPing();
      window.clearTimeout(retryTimer);
      retryTimer = window.setTimeout(connect, retryDelay);
      retryDelay = Math.min(retryDelay * 2, 30000);
    };

    ws.onerror = function () {
      /* onclose reconnects */
    };
  }

  if (navigator.serviceWorker) {
    navigator.serviceWorker.addEventListener("message", function (event) {
      const data = event.data || {};
      if (data.type === "timalove:open" && data.url) {
        window.location.href = data.url;
      }
      if (data.type === "timalove:notification") {
        handleNotification(data.payload || data);
      }
    });
  }

  document.addEventListener("timalove:fcm", function (event) {
    handleNotification(event.detail || {});
  });

  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) {
      connect();
      fetchUnread();
      fetchLikesCount();
      fetchNotificationsCount();
      if (document.body.classList.contains("messages-inbox-page")) {
        document.dispatchEvent(new CustomEvent("timalove:inbox-refresh"));
      }
    }
  });

  window.addEventListener("focus", function () {
    fetchUnread();
    connect();
  });

  window.setInterval(function () {
    fetchUnread();
    fetchNotificationsCount();
  }, POLL_MS);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", connect);
  } else {
    connect();
  }
})();
