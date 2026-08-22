/**
 * Popup de confirmation — activation notifications TimaLove.
 */
(function () {
  const POPUP_ID = "timalove-notif-popup";

  function ensurePopup() {
    let root = document.getElementById(POPUP_ID);
    if (root) return root;

    root = document.createElement("div");
    root.id = POPUP_ID;
    root.className = "notif-popup";
    root.hidden = true;
    root.innerHTML = `
      <div class="notif-popup__backdrop" data-notif-popup-close tabindex="-1"></div>
      <div class="notif-popup__card" role="dialog" aria-modal="true" aria-labelledby="notif-popup-title">
        <span class="notif-popup__icon" data-notif-popup-icon aria-hidden="true">✓</span>
        <h2 class="notif-popup__title" id="notif-popup-title" data-notif-popup-title>Activation réussie</h2>
        <p class="notif-popup__text" data-notif-popup-text></p>
        <button type="button" class="notif-popup__btn" data-notif-popup-close>Compris</button>
      </div>
    `;
    document.body.appendChild(root);

    root.querySelectorAll("[data-notif-popup-close]").forEach((el) => {
      el.addEventListener("click", () => hide());
    });

    return root;
  }

  function hide() {
    const root = document.getElementById(POPUP_ID);
    if (!root) return;
    root.hidden = true;
    document.body.classList.remove("is-notif-popup");
  }

  function show(message, { variant = "success", title } = {}) {
    const root = ensurePopup();
    const isError = variant === "error";
    root.classList.toggle("notif-popup--error", isError);
    root.querySelector("[data-notif-popup-icon]").textContent = isError ? "!" : "✓";
    root.querySelector("[data-notif-popup-title]").textContent =
      title || (isError ? "Activation impossible" : "Activation réussie");
    root.querySelector("[data-notif-popup-text]").textContent = message || "";
    root.hidden = false;
    document.body.classList.add("is-notif-popup");
    root.querySelector(".notif-popup__btn")?.focus();
  }

  window.timaloveNotifPopup = {
    showSuccess(message, opts) {
      show(message, Object.assign({ variant: "success" }, opts || {}));
    },
    showError(message, opts) {
      show(message, Object.assign({ variant: "error", title: "Activation impossible" }, opts || {}));
    },
    hide,
  };
})();
