/**
 * TimaLove — rappel genre pour les membres sans Homme/Femme renseigné.
 * Snooze 10 min (fermeture ou « Plus tard »), puis réaffichage automatique.
 */
(function () {
  const SNOOZE_MS = 10 * 60 * 1000;
  const STORAGE_KEY = "tl_gender_snooze_until";
  const SKIP_PATH_PREFIXES = ["/connexion", "/espace-prive"];

  function cookie(name) {
    const match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[1]) : "";
  }

  function csrf() {
    return cookie("csrftoken");
  }

  function isSnoozed() {
    const until = Number(localStorage.getItem(STORAGE_KEY) || 0);
    return until > Date.now();
  }

  function snoozeRemainingMs() {
    const until = Number(localStorage.getItem(STORAGE_KEY) || 0);
    return Math.max(0, until - Date.now());
  }

  function shouldSkipPath() {
    const path = window.location.pathname || "";
    return SKIP_PATH_PREFIXES.some(function (prefix) {
      return path === prefix || path.startsWith(prefix + "/");
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (document.body.getAttribute("data-needs-gender") !== "1") return;

    const modal = document.getElementById("gender-prompt-modal");
    if (!modal || shouldSkipPath()) return;

    const form = modal.querySelector("[data-gender-prompt-form]");
    const errorEl = modal.querySelector("[data-gender-prompt-error]");
    const select = form && form.querySelector('select[name="gender"]');
    let reshowTimer = 0;
    let busy = false;

    function clearReshowTimer() {
      if (reshowTimer) {
        window.clearTimeout(reshowTimer);
        reshowTimer = 0;
      }
    }

    function scheduleReshow(delayMs) {
      clearReshowTimer();
      if (document.body.getAttribute("data-needs-gender") !== "1") return;
      reshowTimer = window.setTimeout(function () {
        reshowTimer = 0;
        openModal();
      }, Math.max(0, delayMs));
    }

    function showError(message) {
      if (!errorEl) return;
      if (!message) {
        errorEl.hidden = true;
        errorEl.textContent = "";
        return;
      }
      errorEl.hidden = false;
      errorEl.textContent = message;
    }

    function openModal() {
      if (document.body.getAttribute("data-needs-gender") !== "1") return;
      if (shouldSkipPath()) return;
      if (isSnoozed()) {
        scheduleReshow(snoozeRemainingMs());
        return;
      }
      modal.hidden = false;
      document.body.classList.add("is-gender-prompt");
      showError("");
      select && select.focus();
    }

    function closeModal() {
      modal.hidden = true;
      document.body.classList.remove("is-gender-prompt");
    }

    function snooze() {
      localStorage.setItem(STORAGE_KEY, String(Date.now() + SNOOZE_MS));
      closeModal();
      scheduleReshow(SNOOZE_MS);
    }

    modal.querySelectorAll("[data-gender-prompt-snooze]").forEach(function (btn) {
      btn.addEventListener("click", function (event) {
        event.preventDefault();
        snooze();
      });
    });

    form &&
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        if (busy) return;
        const gender = (select && select.value) || "";
        if (gender !== "male" && gender !== "female") {
          showError("Le genre est obligatoire. Choisissez Homme ou Femme.");
          select && select.classList.add("is-invalid");
          return;
        }
        select && select.classList.remove("is-invalid");
        busy = true;
        showError("");
        const saveBtn = modal.querySelector("[data-gender-prompt-save]");
        if (saveBtn) saveBtn.disabled = true;

        fetch("/api/profile/update/", {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrf(),
            "X-Requested-With": "XMLHttpRequest",
          },
          body: JSON.stringify({ gender: gender }),
        })
          .then(function (res) {
            return res.json().then(function (data) {
              return { ok: res.ok, data: data };
            });
          })
          .then(function (result) {
            if (!result.ok || !result.data.ok) {
              const msg =
                (result.data && result.data.errors && result.data.errors.gender) ||
                (result.data && result.data.message) ||
                "Enregistrement impossible.";
              throw new Error(msg);
            }
            localStorage.removeItem(STORAGE_KEY);
            document.body.removeAttribute("data-needs-gender");
            closeModal();
            window.location.reload();
          })
          .catch(function (err) {
            showError(err && err.message ? err.message : "Enregistrement impossible.");
          })
          .finally(function () {
            busy = false;
            if (saveBtn) saveBtn.disabled = false;
          });
      });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !modal.hidden) {
        event.preventDefault();
        snooze();
      }
    });

    openModal();
  });
})();
