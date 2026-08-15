/**
 * TimaLove — likes depuis l’explorer (feed + fiche profil).
 */
(function () {
  function cookie(name) {
    const m = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return m ? decodeURIComponent(m[1]) : "";
  }

  function csrf() {
    return cookie("csrftoken");
  }

  document.addEventListener("click", (event) => {
    const btn = event.target.closest("[data-swipe]");
    if (!btn) return;
    event.preventDefault();
    const root = btn.closest("[data-profile-id]");
    const id = btn.getAttribute("data-profile-id") || (root && root.getAttribute("data-profile-id"));
    const action = btn.getAttribute("data-swipe");
    if (!id || !action || btn.disabled || btn.classList.contains("is-busy")) return;

    btn.classList.add("is-busy");
    fetch("/api/swipes/", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
      body: JSON.stringify({ swiped_id: id, action }),
    })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok || !data.ok) throw new Error(data.error || "Impossible d’enregistrer.");
        const scope = root || document;
        if (action === "like") {
          scope.querySelectorAll('[data-swipe="like"]').forEach((el) => {
            el.classList.add("is-on");
            if (el.classList.contains("visit__dock-btn")) {
              el.setAttribute("aria-label", "Aimé");
            }
          });
        }
        if (action === "super_like") {
          scope.querySelectorAll('[data-swipe="super_like"]').forEach((el) => el.classList.add("is-on"));
        }
        if (action === "pass") {
          scope.querySelectorAll("[data-swipe]").forEach((el) => el.classList.remove("is-on"));
        }
      })
      .catch(() => {})
      .finally(() => {
        btn.classList.remove("is-busy");
      });
  });
})();
