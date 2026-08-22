/**
 * TimaLove — popup connexion invité (dock, explorer, redirection ?gate=1).
 */
(function () {
  const gate = document.getElementById("explorer-gate");
  if (!gate) return;

  function openGate() {
    gate.hidden = false;
    gate.classList.add("is-open");
    document.body.classList.add("is-explorer-gate");
  }

  function closeGate() {
    gate.classList.remove("is-open");
    document.body.classList.remove("is-explorer-gate");
    window.setTimeout(function () {
      if (!gate.classList.contains("is-open")) gate.hidden = true;
    }, 280);
  }

  window.timaloveOpenGate = openGate;
  window.timaloveCloseGate = closeGate;

  const explorerGateSelectors = [
    ".explorer__go-profile",
    ".explorer__action",
    ".explorer__match",
    ".explorer__place",
    ".explorer__meta h2 a",
    ".explorer__icon-btn[href*='inscription']",
    ".explorer__bell",
    "[data-photos]",
  ].join(",");

  document.addEventListener("click", function (event) {
    if (event.target.closest("[data-gate-close]")) {
      event.preventDefault();
      closeGate();
      return;
    }

    if (event.target.closest("[data-gate-open]")) {
      event.preventDefault();
      openGate();
      return;
    }

    if (!document.body.classList.contains("is-guest")) return;

    const trigger = event.target.closest(explorerGateSelectors);
    if (!trigger) return;
    if (event.target.closest("[data-photo-step]")) return;
    event.preventDefault();
    const chip = event.target.closest(".explorer__go-profile");
    if (chip) chip.classList.add("is-pressed");
    window.setTimeout(function () {
      if (chip) chip.classList.remove("is-pressed");
      openGate();
    }, chip ? 180 : 0);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      closeGate();
      return;
    }
    if (!document.body.classList.contains("is-guest")) return;
    if (
      (event.key === "Enter" || event.key === " ") &&
      event.target.closest(".explorer__match, .explorer__place")
    ) {
      event.preventDefault();
      openGate();
    }
  });

  const params = new URLSearchParams(window.location.search);
  if (params.get("gate") === "1") {
    openGate();
    params.delete("gate");
    const qs = params.toString();
    const next = window.location.pathname + (qs ? "?" + qs : "") + window.location.hash;
    window.history.replaceState({}, "", next);
  }
})();
