/**
 * TimaLove — resynchronise l’explorer après déploiement ou changement de règles feed.
 * Recharge la page si la révision deploy serveur ≠ sessionStorage (effet immédiat au refresh / retour onglet).
 */
(function () {
  const meta = document.querySelector('meta[name="timalove-deploy-revision"]');
  if (!meta) return;

  const rev = (meta.getAttribute("content") || "").trim();
  if (!rev) return;

  const KEY = "timalove_deploy_rev";

  function applyRevision() {
    const stored = sessionStorage.getItem(KEY);
    if (stored && stored !== rev) {
      sessionStorage.setItem(KEY, rev);
      window.location.reload();
      return true;
    }
    sessionStorage.setItem(KEY, rev);
    return false;
  }

  if (applyRevision()) return;

  window.addEventListener("pageshow", function (event) {
    if (!event.persisted) return;
    const stored = sessionStorage.getItem(KEY);
    if (stored && stored !== rev) {
      sessionStorage.setItem(KEY, rev);
      window.location.reload();
    }
  });

  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState !== "visible") return;
    const live = (meta.getAttribute("content") || "").trim();
    const stored = sessionStorage.getItem(KEY);
    if (stored && live && stored !== live) {
      sessionStorage.setItem(KEY, live);
      window.location.reload();
    }
  });
})();
