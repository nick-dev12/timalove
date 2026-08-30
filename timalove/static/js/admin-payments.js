(function () {
  const COLORS = {
    rose: "#E8637A",
    bordeaux: "#2D1F22",
    bordeauxMedium: "#5C3A3F",
    secondary: "#C4858B",
    vip: "#D4A017",
    success: "#4CAF50",
    info: "#2196F3",
    cream: "#FDF5F0",
  };

  const PALETTE = [COLORS.rose, COLORS.bordeauxMedium, COLORS.secondary, COLORS.vip, COLORS.info, COLORS.success];

  function readChannelData() {
    const node = document.getElementById("finance-channels-data");
    if (!node) return null;
    try {
      return JSON.parse(node.textContent);
    } catch (_err) {
      return null;
    }
  }

  function initChart() {
    if (typeof Chart === "undefined") return;
    const data = readChannelData();
    const canvas = document.getElementById("finance-channels-chart");
    if (!canvas || !data || !data.labels?.length) return;

    Chart.defaults.font.family = "'DM Sans', sans-serif";
    Chart.defaults.color = COLORS.bordeaux;

    new Chart(canvas, {
      type: "doughnut",
      data: {
        labels: data.labels,
        datasets: [
          {
            data: data.values,
            backgroundColor: data.labels.map((_, i) => PALETTE[i % PALETTE.length]),
            borderWidth: 0,
            hoverOffset: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "58%",
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              color: COLORS.bordeaux,
              boxWidth: 12,
              usePointStyle: true,
              padding: 14,
            },
          },
          tooltip: {
            backgroundColor: COLORS.bordeaux,
            callbacks: {
              label(context) {
                const value = context.raw || 0;
                return ` ${context.label} : ${Number(value).toLocaleString("fr-FR")} FCFA`;
              },
            },
          },
        },
      },
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initChart();

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
    const metaTpl = document.getElementById("payments-page-meta");
    if (!toolbar || !tbody || !searchInput) return;

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
      if (exportCsv) exportCsv.href = `${window.location.pathname}${suffix}export=csv`;
      if (exportExcel) exportExcel.href = `${window.location.pathname}${suffix}export=excel`;
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
      if (statusEl) {
        statusEl.textContent = total
          ? `${shown} affiché(s) sur ${total} transaction(s)`
          : "Aucun résultat";
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
      const q = searchInput.value.trim();
      try {
        const res = await fetch(`${window.location.pathname}?${buildParams(page).toString()}`, {
          headers: { "X-Requested-With": "XMLHttpRequest" },
          credentials: "same-origin",
        });
        if (!res.ok) throw new Error("fetch");
        const html = await res.text();
        const total = Number(res.headers.get("X-Payments-Total") || 0);
        const hasNext = res.headers.get("X-Payments-Has-Next") === "1";
        const nextPage = res.headers.get("X-Payments-Next-Page") || "";

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
        syncExportLinks();
      } catch (_err) {
        if (statusEl) statusEl.textContent = "Filtrage indisponible. Réessayez.";
      } finally {
        loading = false;
      }
    }

    function scheduleFetch() {
      window.clearTimeout(debounceTimer);
      debounceTimer = window.setTimeout(() => {
        fetchRows({ page: 1, append: false });
      }, 320);
    }

    searchInput.addEventListener("input", scheduleFetch);
    clearBtn?.addEventListener("click", () => {
      searchInput.value = "";
      fetchRows({ page: 1, append: false });
    });

    [statusSelect, productSelect, periodSelect, dateFrom, dateTo].forEach((el) => {
      el?.addEventListener("change", () => fetchRows({ page: 1, append: false }));
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

    if (metaTpl) {
      applyMeta({
        total: Number(metaTpl.dataset.total || 0),
        hasNext: metaTpl.dataset.hasNext === "1",
        nextPage: metaTpl.dataset.nextPage || "",
        shown: tbody.querySelectorAll("tr").length,
      });
    }
    syncExportLinks();
  });
})();
