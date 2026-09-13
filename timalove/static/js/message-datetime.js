/**
 * TimaLove — horodatage messages : UTC côté serveur, fuseau local de l'appareil côté client.
 */
(function (global) {
  function formatMessageDate(isoDateString) {
    if (!isoDateString) return "";

    const messageDate = new Date(isoDateString);
    if (Number.isNaN(messageDate.getTime())) return "";

    const now = new Date();
    const timeStr = messageDate.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });

    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    const msgDay = new Date(
      messageDate.getFullYear(),
      messageDate.getMonth(),
      messageDate.getDate()
    );

    if (msgDay.getTime() === today.getTime()) {
      return timeStr;
    }

    if (msgDay.getTime() === yesterday.getTime()) {
      return "Hier " + timeStr;
    }

    if (messageDate.getFullYear() === now.getFullYear()) {
      const dayMonth = messageDate.toLocaleDateString("fr-FR", {
        day: "numeric",
        month: "short",
      });
      return dayMonth + " à " + timeStr;
    }

    return messageDate.toLocaleDateString("fr-FR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  }

  function formatInboxTime(isoDateString) {
    if (!isoDateString) return "";

    const messageDate = new Date(isoDateString);
    if (Number.isNaN(messageDate.getTime())) return "";

    const now = new Date();
    const timeStr = messageDate.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });

    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    const msgDay = new Date(
      messageDate.getFullYear(),
      messageDate.getMonth(),
      messageDate.getDate()
    );

    if (msgDay.getTime() === today.getTime()) {
      return timeStr;
    }

    if (msgDay.getTime() === yesterday.getTime()) {
      return "Hier";
    }

    return messageDate.toLocaleDateString("fr-FR", {
      day: "2-digit",
      month: "2-digit",
    });
  }

  function formatMessageTime(item) {
    if (item && item.created_at) {
      return formatMessageDate(item.created_at);
    }
    return (item && item.time) || "";
  }

  function applyMessageTimes(root) {
    const scope = root || document;
    scope.querySelectorAll("time[datetime]").forEach(function (el) {
      const iso = el.getAttribute("datetime");
      if (!iso) return;
      const mode = el.getAttribute("data-time-mode") || "thread";
      el.textContent =
        mode === "inbox" ? formatInboxTime(iso) : formatMessageDate(iso);
    });
  }

  global.timaloveFormatMessageDate = formatMessageDate;
  global.timaloveFormatInboxTime = formatInboxTime;
  global.timaloveFormatMessageTime = formatMessageTime;
  global.timaloveApplyMessageTimes = applyMessageTimes;
})(window);
