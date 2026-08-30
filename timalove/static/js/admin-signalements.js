(function () {
  document.addEventListener("DOMContentLoaded", () => {
    const toolbar = document.querySelector("[data-reports-toolbar]");
    const tbody = document.querySelector("[data-reports-tbody]");
    const searchInput = document.querySelector("[data-reports-search]");
    const statusSelect = document.querySelector("[data-reports-status]");
    const prioritySelect = document.querySelector("[data-reports-priority]");
    const clearBtn = document.querySelector("[data-reports-clear]");
    const moreBtn = document.querySelector("[data-reports-more]");
    const statusEl = document.querySelector("[data-reports-status-text]");
    const metaTpl = document.getElementById("reports-page-meta");
    if (!toolbar || !tbody || !searchInput) return;

    let debounceTimer = null;
    let loading = false;

    function readMeta() {
      const tpl = document.getElementById("reports-page-meta");
      if (!tpl) return { hasNext: false, nextPage: "", total: 0, shown: 0 };
      return {
        hasNext: tpl.dataset.hasNext === "1",
        nextPage: tpl.dataset.nextPage || "",
        total: Number(tpl.dataset.total || 0),
        shown: Number(tpl.dataset.shown || 0),
      };
    }

    function applyMeta({ total, hasNext, nextPage, shown }) {
      const tpl = document.getElementById("reports-page-meta");
      if (tpl) {
        tpl.dataset.total = String(total);
        tpl.dataset.hasNext = hasNext ? "1" : "0";
        tpl.dataset.nextPage = nextPage || "";
        tpl.dataset.shown = String(shown);
      }
      if (moreBtn) moreBtn.hidden = !hasNext;
      if (statusEl) {
        statusEl.textContent = total
          ? `${shown} affiché(s) sur ${total} signalement(s) — tri par urgence`
          : "Aucun résultat";
      }
    }

    function buildParams(page) {
      const params = new URLSearchParams({ format: "partial", page: String(page) });
      const q = searchInput.value.trim();
      if (q) params.set("q", q);
      if (statusSelect?.value) params.set("status", statusSelect.value);
      if (prioritySelect?.value) params.set("priority", prioritySelect.value);
      return params;
    }

    async function fetchRows({ page, append }) {
      if (loading) return;
      loading = true;
      const q = searchInput.value.trim();
      try {
        const res = await fetch(`${window.location.pathname}?${buildParams(page).toString()}`, {
          headers: { "X-Requested-With": "XMLHttpRequest" },
          credentials: "same-origin",
        });
        if (!res.ok) throw new Error("fetch");
        const html = await res.text();
        const total = Number(res.headers.get("X-Reports-Total") || 0);
        const hasNext = res.headers.get("X-Reports-Has-Next") === "1";
        const nextPage = res.headers.get("X-Reports-Next-Page") || "";

        if (append) {
          const parser = new DOMParser();
          const doc = parser.parseFromString(`<table><tbody>${html}</tbody></table>`, "text/html");
          doc.querySelectorAll("tr").forEach((row) => tbody.appendChild(row));
        } else {
          tbody.innerHTML = html;
        }

        applyMeta({
          total,
          hasNext,
          nextPage,
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
      debounceTimer = window.setTimeout(() => {
        fetchRows({ page: 1, append: false });
      }, 320);
    });

    clearBtn?.addEventListener("click", () => {
      searchInput.value = "";
      fetchRows({ page: 1, append: false });
    });

    statusSelect?.addEventListener("change", () => {
      fetchRows({ page: 1, append: false });
    });

    prioritySelect?.addEventListener("change", () => {
      fetchRows({ page: 1, append: false });
    });

    moreBtn?.addEventListener("click", () => {
      const meta = readMeta();
      if (!meta.hasNext || !meta.nextPage) return;
      fetchRows({ page: Number(meta.nextPage), append: true });
    });

    if (metaTpl) {
      applyMeta({
        total: Number(metaTpl.dataset.total || 0),
        hasNext: metaTpl.dataset.hasNext === "1",
        nextPage: metaTpl.dataset.nextPage || "",
        shown: tbody.querySelectorAll("tr").length,
      });
    }
  });
})();
