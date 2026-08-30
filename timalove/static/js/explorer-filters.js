/**
 * TimaLove — popup filtres rapides sur l’explorer.
 */
(function () {
  const modal = document.getElementById("explorer-filters-modal");
  const form = document.querySelector("[data-explorer-filters-form]");
  const saveBtn = document.querySelector("[data-explorer-filters-save]");
  const msgEl = document.querySelector("[data-explorer-filters-msg]");
  const openBtn = document.querySelector("[data-explorer-filters-open]");

  if (!modal || !form || !openBtn) return;

  function csrf() {
    const m = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  function openModal() {
    modal.hidden = false;
    document.body.classList.add("is-explorer-filters");
    const first = form.querySelector("input, select");
    if (first) first.focus();
  }

  function closeModal() {
    modal.hidden = true;
    document.body.classList.remove("is-explorer-filters");
    if (msgEl) {
      msgEl.hidden = true;
      msgEl.textContent = "";
    }
  }

  openBtn.addEventListener("click", function (event) {
    event.preventDefault();
    openModal();
  });

  modal.querySelectorAll("[data-explorer-filters-close]").forEach(function (btn) {
    btn.addEventListener("click", function (event) {
      event.preventDefault();
      closeModal();
    });
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && !modal.hidden) closeModal();
  });

  saveBtn?.addEventListener("click", function () {
    if (!saveBtn || saveBtn.disabled) return;
    const fd = new FormData(form);
    saveBtn.disabled = true;
    if (msgEl) {
      msgEl.hidden = true;
      msgEl.textContent = "";
    }
    fetch("/api/profile/filters/", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf(),
      },
      body: JSON.stringify({
        age_min: fd.get("age_min"),
        age_max: fd.get("age_max"),
        religion: fd.get("religion"),
        country: fd.get("country"),
        verified_only: fd.get("verified_only") === "on",
        online_only: fd.get("online_only") === "on",
      }),
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (result) {
        if (!result.ok || !result.data.ok) {
          throw new Error((result.data && result.data.message) || "Enregistrement impossible.");
        }
        window.location.assign("/explorer/");
      })
      .catch(function (err) {
        if (msgEl) {
          msgEl.textContent = err.message || "Erreur lors de l’enregistrement.";
          msgEl.hidden = false;
        }
      })
      .finally(function () {
        saveBtn.disabled = false;
      });
  });
})();
