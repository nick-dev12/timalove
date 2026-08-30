(function () {
  if (window.timaloveCrmPopups) return;
  window.timaloveCrmPopups = true;

  const seen = new Set();
  let pollTimer = null;

  function schedule(seconds) {
    window.clearTimeout(pollTimer);
    pollTimer = window.setTimeout(poll, Math.max(15, seconds) * 1000);
  }

  async function poll() {
    if (window.location.pathname.startsWith("/espace-prive")) return;
    try {
      const res = await fetch("/api/crm/popups/", {
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      if (!res.ok) return;
      const data = await res.json();
      schedule(Number(data.pollSeconds) || 45);
      if (data.showOnEveryPage === false) {
        if (data.showOnLogin === false) return;
        if (sessionStorage.getItem("tl-crm-login-shown") === "1") return;
      }
      const popups = Array.isArray(data.popups) ? data.popups : [];
      for (const popup of popups) {
        const id = popup.delivery_id || popup.id;
        if (!id || seen.has(id)) continue;
        seen.add(id);
        if (data.showOnEveryPage === false) {
          sessionStorage.setItem("tl-crm-login-shown", "1");
        }
        if (typeof window.timaloveShowLivePopup === "function") {
          window.timaloveShowLivePopup(popup);
        }
        break;
      }
    } catch (_err) {
      schedule(45);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (window.location.pathname.startsWith("/espace-prive")) return;
    void poll();
  });
})();
