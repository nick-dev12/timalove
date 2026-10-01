/**
 * TimaLove — projet de mariage obligatoire.
 * Modal non fermable, réaffiché à chaque visite tant que le projet est incomplet.
 */
(function () {
  const SKIP_PATH_PREFIXES = [
    "/connexion",
    "/inscription",
    "/onboarding",
    "/completer-profil",
    "/espace-prive",
    "/mot-de-passe",
  ];
  const FIELDS = [
    "marriage_timeline",
    "union_type",
    "children_wish",
    "partner_religion_importance",
    "meet_place",
  ];

  function cookie(name) {
    const match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[1]) : "";
  }

  function csrf() {
    return cookie("csrftoken") || document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
  }

  function shouldSkipPath() {
    const path = window.location.pathname || "";
    return SKIP_PATH_PREFIXES.some(function (prefix) {
      return path === prefix || path.startsWith(prefix + "/");
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (document.body.getAttribute("data-needs-projet") !== "1") return;

    const modal = document.getElementById("projet-prompt-modal");
    if (!modal || shouldSkipPath()) return;

    const form = modal.querySelector("[data-projet-prompt-form]");
    const errorEl = modal.querySelector("[data-projet-prompt-error]");
    let busy = false;

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

    function selectedValue(field) {
      const on = form && form.querySelector('[data-field-set="' + field + '"].is-on');
      return on ? on.getAttribute("data-value") || "" : "";
    }

    function openModal() {
      if (shouldSkipPath()) return;
      modal.hidden = false;
      document.body.classList.add("is-projet-prompt");
      showError("");
      const first = form && form.querySelector(".cdc-choice__item");
      first && first.focus();
    }

    form &&
      form.querySelectorAll("[data-field-set]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          const field = btn.getAttribute("data-field-set");
          form.querySelectorAll('[data-field-set="' + field + '"]').forEach(function (other) {
            other.classList.remove("is-on");
            other.setAttribute("aria-pressed", "false");
          });
          btn.classList.add("is-on");
          btn.setAttribute("aria-pressed", "true");
          showError("");
        });
      });

    form &&
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        if (busy) return;
        const payload = {};
        const missing = [];
        FIELDS.forEach(function (field) {
          payload[field] = selectedValue(field);
          if (!payload[field]) missing.push(field);
        });
        if (missing.length) {
          showError("Pour continuer, veuillez remplir votre projet.");
          return;
        }
        busy = true;
        showError("");
        const saveBtn = modal.querySelector("[data-projet-prompt-save]");
        if (saveBtn) saveBtn.disabled = true;

        fetch("/api/profile/update/", {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrf(),
            "X-Requested-With": "XMLHttpRequest",
          },
          body: JSON.stringify(payload),
        })
          .then(function (res) {
            return res.json().then(function (data) {
              return { ok: res.ok, data: data };
            });
          })
          .then(function (result) {
            if (!result.ok || !result.data.ok) {
              const errors = (result.data && result.data.errors) || {};
              const first = Object.keys(errors)[0];
              throw new Error(
                (first && errors[first]) ||
                  (result.data && result.data.message) ||
                  "Enregistrement impossible."
              );
            }
            document.body.removeAttribute("data-needs-projet");
            document.body.classList.remove("is-projet-prompt");
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
        event.stopPropagation();
      }
    });

    openModal();
  });
})();
