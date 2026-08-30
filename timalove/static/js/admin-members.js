(function () {
  document.addEventListener("DOMContentLoaded", () => {
    const toolbar = document.querySelector("[data-members-toolbar]");
    const tbody = document.querySelector("[data-members-tbody]");
    const searchInput = document.querySelector("[data-members-search]");
    const statusSelect = document.querySelector("[data-members-account-status]");
    const subSelect = document.querySelector("[data-members-subscription]");
    const clearBtn = document.querySelector("[data-members-clear]");
    const moreBtn = document.querySelector("[data-members-more]");
    const statusEl = document.querySelector("[data-members-status]");
    const metaTpl = document.getElementById("members-page-meta");
    if (!toolbar || !tbody || !searchInput) return;

    let debounceTimer = null;
    let loading = false;
    let currentPage = 1;

    function parsePage(value) {
      const n = parseInt(String(value ?? ""), 10);
      return Number.isFinite(n) && n > 0 ? n : null;
    }

    function readMeta() {
      const tpl = document.getElementById("members-page-meta");
      if (!tpl) return { hasNext: false, nextPage: "", total: 0, shown: 0 };
      return {
        hasNext: tpl.dataset.hasNext === "1",
        nextPage: tpl.dataset.nextPage || "",
        total: Number(tpl.dataset.total || 0),
        shown: Number(tpl.dataset.shown || 0),
      };
    }

    function applyMeta({ total, hasNext, nextPage, shown }) {
      const tpl = document.getElementById("members-page-meta");
      if (tpl) {
        tpl.dataset.total = String(total);
        tpl.dataset.hasNext = hasNext ? "1" : "0";
        tpl.dataset.nextPage = nextPage ? String(nextPage) : "";
        tpl.dataset.shown = String(shown);
      }
      if (moreBtn) moreBtn.hidden = !hasNext;
      if (statusEl) {
        statusEl.textContent = total
          ? `${shown} affiché(s) sur ${total} utilisateur(s)`
          : "Aucun résultat";
      }
    }

    function buildParams(page) {
      const safePage = parsePage(page) ?? 1;
      const params = new URLSearchParams({ format: "partial", page: String(safePage) });
      const q = searchInput.value.trim();
      if (q) params.set("q", q);
      if (statusSelect?.value) params.set("account_status", statusSelect.value);
      if (subSelect?.value) params.set("subscription_kind", subSelect.value);
      return params;
    }

    async function fetchRows({ page, append }) {
      if (loading) return;
      const safePage = parsePage(page) ?? 1;
      loading = true;
      const q = searchInput.value.trim();
      try {
        const res = await fetch(`${window.location.pathname}?${buildParams(safePage).toString()}`, {
          headers: { "X-Requested-With": "XMLHttpRequest" },
          credentials: "same-origin",
        });
        if (!res.ok) throw new Error("fetch");
        const html = await res.text();
        const total = Number(res.headers.get("X-Members-Total") || 0);
        const hasNext = res.headers.get("X-Members-Has-Next") === "1";
        const headerNext = parsePage(res.headers.get("X-Members-Next-Page"));

        if (append) {
          currentPage = safePage;
          const parser = new DOMParser();
          const doc = parser.parseFromString(`<table><tbody>${html}</tbody></table>`, "text/html");
          doc.querySelectorAll("tr").forEach((row) => tbody.appendChild(row));
        } else {
          currentPage = 1;
          tbody.innerHTML = html;
        }

        const nextPage = headerNext ?? (hasNext ? currentPage + 1 : null);
        applyMeta({
          total,
          hasNext,
          nextPage: nextPage ? String(nextPage) : "",
          shown: tbody.querySelectorAll("tr").length,
        });
        if (clearBtn) clearBtn.hidden = !q;
      } catch (_err) {
        if (statusEl) statusEl.textContent = "Recherche indisponible. Réessayez.";
      } finally {
        loading = false;
      }
    }

    searchInput.addEventListener("input", () => {
      window.clearTimeout(debounceTimer);
      debounceTimer = window.setTimeout(() => fetchRows({ page: 1, append: false }), 320);
    });

    clearBtn?.addEventListener("click", () => {
      searchInput.value = "";
      fetchRows({ page: 1, append: false });
    });

    statusSelect?.addEventListener("change", () => fetchRows({ page: 1, append: false }));
    subSelect?.addEventListener("change", () => fetchRows({ page: 1, append: false }));

    moreBtn?.addEventListener("click", () => {
      const meta = readMeta();
      if (!meta.hasNext) return;
      const next = parsePage(meta.nextPage) ?? currentPage + 1;
      fetchRows({ page: next, append: true });
    });

    if (metaTpl) {
      currentPage = 1;
      applyMeta({
        total: Number(metaTpl.dataset.total || 0),
        hasNext: metaTpl.dataset.hasNext === "1",
        nextPage: metaTpl.dataset.nextPage || "",
        shown: tbody.querySelectorAll("tr").length,
      });
    }
  });
})();
