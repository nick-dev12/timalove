/**
 * TimaLove — modal abonnements (quota messages, swipes, likes, historique).
 */
(function () {
  function csrf() {
    const m = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
    if (m) return decodeURIComponent(m[1]);
    const field = document.querySelector("[name=csrfmiddlewaretoken]");
    return field ? field.value : "";
  }

  function modal() {
    return document.getElementById("settings-modal-subscription");
  }

  function open() {
    const el = modal();
    if (!el) return false;
    el.hidden = false;
    document.body.classList.add("is-settings-modal");
    const closeBtn = el.querySelector("[data-settings-modal-close]");
    if (closeBtn) closeBtn.focus();
    return true;
  }

  function close() {
    const el = modal();
    if (!el) return;
    el.hidden = true;
    document.body.classList.remove("is-settings-modal");
  }

  function isLimitError(err) {
    if (!err) return false;
    const code = err.code || (err.data && err.data.code);
    if (code === "message_limit" || code === "like_limit" || code === "swipe_limit") return true;
    const message = err.message || err.error || (err.data && (err.data.error || err.data.message)) || "";
    return /limite/i.test(message);
  }

  function handleLimitError(err) {
    if (!isLimitError(err)) return false;
    if (!open()) {
      const message = err.message || err.error || (err.data && err.data.error) || "Passez au plan supérieur pour continuer.";
      let toast = document.getElementById("swipe-toast");
      if (!toast) {
        toast = document.createElement("div");
        toast.id = "swipe-toast";
        toast.className = "swipe-toast";
        toast.setAttribute("role", "status");
        document.body.appendChild(toast);
      }
      toast.textContent = message;
      toast.hidden = false;
    }
    return true;
  }

  function bindModal() {
    const el = modal();
    if (!el || el.dataset.subscriptionBound === "1") return;
    el.dataset.subscriptionBound = "1";

    el.querySelectorAll("[data-settings-modal-close]").forEach(function (node) {
      node.addEventListener("click", close);
    });

    const plansStatus = el.querySelector("[data-save-msg='subscription']");

    el.addEventListener("click", function (event) {
      const btn = event.target.closest("[data-checkout]");
      if (!btn || btn.disabled) return;
      event.preventDefault();
      const original = btn.textContent;
      btn.disabled = true;
      btn.textContent = "Ouverture du paiement…";
      if (plansStatus) {
        plansStatus.hidden = true;
        plansStatus.textContent = "";
      }
      fetch("/api/payments/checkout/", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf(),
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({ tier: btn.getAttribute("data-checkout") }),
      })
        .then(function (res) {
          return res.json().then(function (payload) {
            if (!res.ok || !payload.ok) {
              throw new Error((payload && payload.message) || "Lien de paiement indisponible.");
            }
            return payload;
          });
        })
        .then(function (data) {
          if (!data.checkout_url) throw new Error("Lien de paiement indisponible.");
          window.location.href = data.checkout_url;
        })
        .catch(function (err) {
          if (plansStatus) {
            plansStatus.hidden = false;
            plansStatus.textContent = err.message || "Paiement indisponible pour le moment.";
          }
        })
        .finally(function () {
          btn.disabled = false;
          btn.textContent = original;
        });
    });
  }

  document.addEventListener("click", function (event) {
    const trigger = event.target.closest("[data-subscription-upgrade]");
    if (!trigger) return;
    event.preventDefault();
    open();
  });

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") return;
    const el = modal();
    if (el && !el.hidden) close();
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindModal);
  } else {
    bindModal();
  }

  window.timaloveSubscriptionModal = {
    open: open,
    close: close,
    isLimitError: isLimitError,
    handleLimitError: handleLimitError,
  };
})();
