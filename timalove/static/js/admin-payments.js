(function () {
  document.addEventListener("DOMContentLoaded", () => {
    const live = window.AdmLive;
    const cfg = document.getElementById("payments-async-config");
    const toolbar = document.querySelector("[data-payments-toolbar]");
    const tbody = document.querySelector("[data-payments-tbody]");
    const searchInput = document.querySelector("[data-payments-search]");
    const statusSelect = document.querySelector("[data-payments-status]");
    const productSelect = document.querySelector("[data-payments-product]");
    const periodSelect = document.querySelector("[data-payments-period]");
    const dateFrom = document.querySelector("[data-payments-from]");
    const dateTo = document.querySelector("[data-payments-to]");
    const clearBtn = document.querySelector("[data-payments-clear]");
    const moreBtn = document.querySelector("[data-payments-more]");
    const statusEl = document.querySelector("[data-payments-status-text]");
    const exportCsv = document.querySelector("[data-payments-export-csv]");
    const exportExcel = document.querySelector("[data-payments-export-excel]");
    const statsWrap = document.querySelector("[data-payments-stats]");
    const channelsWrap = document.querySelector("[data-payments-channels]");
    const tableWrap = document.querySelector("[data-payments-table-wrap]");
    if (!live || !cfg || !toolbar || !tbody || !searchInput) return;

    let debounceTimer = null;
    let loading = false;

    function filterQuery() {
      const params = new URLSearchParams();
      const q = searchInput.value.trim();
      if (q) params.set("q", q);
      if (statusSelect?.value) params.set("status", statusSelect.value);
      if (productSelect?.value) params.set("product_type", productSelect.value);
      if (periodSelect?.value) params.set("period", periodSelect.value);
      if (dateFrom?.value) params.set("date_from", dateFrom.value);
      if (dateTo?.value) params.set("date_to", dateTo.value);
      return params;
    }

    function syncExportLinks() {
      const qs = filterQuery().toString();
      const suffix = qs ? `?${qs}&` : "?";
      const base = cfg.dataset.partialBase || window.location.pathname;
      if (exportCsv) exportCsv.href = `${base}${suffix}export=csv`;
      if (exportExcel) exportExcel.href = `${base}${suffix}export=excel`;
    }

    function readMeta() {
      const tpl = document.getElementById("payments-page-meta");
      if (!tpl) return { hasNext: false, nextPage: "", total: 0, shown: 0 };
      return {
        hasNext: tpl.dataset.hasNext === "1",
        nextPage: tpl.dataset.nextPage || "",
        total: Number(tpl.dataset.total || 0),
        shown: Number(tpl.dataset.shown || 0),
      };
    }

    function applyMeta({ total, hasNext, nextPage, shown }) {
      const tpl = document.getElementById("payments-page-meta");
      if (tpl) {
        tpl.dataset.total = String(total);
        tpl.dataset.hasNext = hasNext ? "1" : "0";
        tpl.dataset.nextPage = nextPage || "";
        tpl.dataset.shown = String(shown);
      }
      if (moreBtn) moreBtn.hidden = !hasNext;
      if (statusEl && !loading) {
        statusEl.textContent = total
          ? `${shown} affiché(s) sur ${total} transaction(s)`
          : "Aucun résultat";
      }
    }

    function countDataRows() {
      return tbody.querySelectorAll("tr:not(.adm-empty-row):not(.adm-skeleton-row)").length;
    }

    function applySummary(summary, error) {
      if (!summary) return;
      const fields = {
        "paid-amount": summary.paid_amount_label,
        "paid-count": summary.paid_count,
        "failed-amount": summary.failed_amount_label,
        "failed-count": summary.failed_count,
        "refunded-amount": summary.refunded_amount_label,
        "refunded-count": summary.refunded_count,
        "dispute-count": summary.dispute_count,
      };
      Object.entries(fields).forEach(([key, value]) => {
        document.querySelectorAll(`[data-stat-${key}]`).forEach((el) => {
          el.textContent = value ?? "—";
        });
      });
      if (channelsWrap) {
        channelsWrap.hidden = false;
        live.buildChannelMini(summary.channels, channelsWrap.querySelector("[data-channels-list]"));
        live.reveal(channelsWrap);
      }
      live.reveal(statsWrap);
      if (error && statusEl) {
        statusEl.textContent = `${error} — liste partielle affichée si disponible.`;
      }
    }

    async function fetchSummary() {
      const params = filterQuery();
      const url = `${cfg.dataset.summaryUrl}?${params.toString()}`;
      try {
        const data = await live.fetchJson(url);
        live.applySyncMeta(data.sync);
        applySummary(data.summary, data.error);
      } catch (_err) {
        if (statusEl) statusEl.textContent = "Résumé financier indisponible.";
      }
    }

    function buildParams(page) {
      const params = filterQuery();
      params.set("format", "partial");
      params.set("page", String(page));
      return params;
    }

    async function fetchRows({ page, append }) {
      if (loading) return;
      loading = true;
      live.markPending();
      if (moreBtn) {
        moreBtn.disabled = true;
        moreBtn.textContent = append ? "Chargement…" : moreBtn.textContent;
      }
      if (!append && statusEl) statusEl.textContent = "Chargement des transactions…";
      const q = searchInput.value.trim();
      const base = cfg.dataset.partialBase || window.location.pathname;
      try {
        const res = await fetch(`${base}?${buildParams(page).toString()}`, {
          headers: { "X-Requested-With": "XMLHttpRequest" },
          credentials: "same-origin",
        });
        if (!res.ok) throw new Error("fetch");
        const html = await res.text();
        const total = Number(res.headers.get("X-Payments-Total") || 0);
        const hasNext = res.headers.get("X-Payments-Has-Next") === "1";
        const nextPage = res.headers.get("X-Payments-Next-Page") || "";

        if (append) {
          const wrap = document.createElement("tbody");
          wrap.innerHTML = html;
          wrap.querySelectorAll("tr").forEach((row) => {
            if (!row.querySelector(".adm-empty")) tbody.appendChild(row);
          });
        } else {
          tbody.innerHTML = html;
        }

        applyMeta({
          total,
          hasNext,
          nextPage,
          shown: countDataRows(),
        });
        if (clearBtn) clearBtn.hidden = !q;
        syncExportLinks();
        live.reveal(tableWrap);
      } catch (_err) {
        if (statusEl) statusEl.textContent = "Chargement indisponible. Réessayez.";
      } finally {
        loading = false;
        live.markDone();
        if (moreBtn) {
          moreBtn.disabled = false;
          moreBtn.textContent = "Voir plus";
        }
      }
    }

    function reloadAll() {
      fetchSummary();
      fetchRows({ page: 1, append: false });
    }

    function scheduleReload() {
      window.clearTimeout(debounceTimer);
      debounceTimer = window.setTimeout(reloadAll, 320);
    }

    searchInput.addEventListener("input", scheduleReload);
    clearBtn?.addEventListener("click", () => {
      searchInput.value = "";
      reloadAll();
    });

    [statusSelect, productSelect, periodSelect, dateFrom, dateTo].forEach((el) => {
      el?.addEventListener("change", reloadAll);
    });

    moreBtn?.addEventListener("click", () => {
      const meta = readMeta();
      if (!meta.hasNext || !meta.nextPage) return;
      fetchRows({ page: Number(meta.nextPage), append: true });
    });

    document.addEventListener("submit", (e) => {
      const form = e.target.closest("form[data-confirm]");
      if (form && !window.confirm(form.dataset.confirm)) e.preventDefault();
    });

    syncExportLinks();
    Promise.all([fetchSummary(), fetchRows({ page: 1, append: false })]);
  });
})();
