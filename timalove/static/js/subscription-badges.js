/**
 * Badges abonnement Premium / VIP — rendu client (inbox live, etc.).
 */
(function () {
  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function markHtml(badge, labeled) {
    if (badge === "vip") {
      return (
        '<span class="tl-mark tl-mark--vip" title="VIP" aria-label="VIP">VIP</span>'
      );
    }
    if (badge === "premium") {
      if (labeled) {
        return (
          '<span class="tl-mark tl-mark--premium" title="Premium" aria-label="Premium">Premium</span>'
        );
      }
      return (
        '<span class="tl-mark tl-mark--cert" title="Premium" aria-label="Compte Premium">' +
        '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">' +
        '<circle cx="12" cy="12" r="12" fill="currentColor"/>' +
        '<path fill="none" stroke="#fff" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" d="M7 12.2 10.2 15.4 17 8.6"/>' +
        "</svg></span>"
      );
    }
    return "";
  }

  function slideClass(badge) {
    if (badge === "vip") return " is-vip";
    if (badge === "premium") return " is-premium";
    return "";
  }

  window.timaloveSubscriptionMark = markHtml;
  window.timaloveSubscriptionSlideClass = slideClass;
  window.timaloveSubscriptionEscape = escapeHtml;
})();
