(function () {
  const COLORS = {
    rose: "#E8637A",
    rosePale: "#FFF0F3",
    bordeaux: "#2D1F22",
    bordeauxMedium: "#5C3A3F",
    secondary: "#C4858B",
    vip: "#D4A017",
    success: "#4CAF50",
    error: "#E53935",
    info: "#2196F3",
    cream: "#FDF5F0",
    white: "#FFFFFF",
  };

  const PALETTE = [COLORS.rose, COLORS.bordeauxMedium, COLORS.secondary, COLORS.vip, COLORS.info, COLORS.success];

  function baseOptions(extra = {}) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: {
            color: COLORS.bordeaux,
            font: { family: "'DM Sans', sans-serif", size: 12 },
            boxWidth: 12,
            usePointStyle: true,
          },
        },
        tooltip: {
          backgroundColor: COLORS.bordeaux,
          titleColor: COLORS.white,
          bodyColor: COLORS.rosePale,
          padding: 10,
          cornerRadius: 8,
        },
      },
      ...extra,
    };
  }

  function lineDataset(label, data, color) {
    return {
      label,
      data,
      borderColor: color,
      backgroundColor: color,
      borderWidth: 2,
      pointRadius: 2,
      pointHoverRadius: 4,
      tension: 0.25,
      fill: false,
    };
  }

  function trendPrefix(trend) {
    if (trend === "up") return "+";
    if (trend === "down") return "-";
    return "";
  }

  function formatDate(iso) {
    if (!iso) return "—";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "—";
    return d.toLocaleString("fr-FR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function statusBadgeClass(status) {
    if (status === "paid") return "ok";
    if (status === "failed") return "danger";
    if (status === "pending") return "warn";
    return "muted";
  }

  function renderKpis(kpis) {
    const wrap = document.querySelector("[data-dashboard-kpis]");
    if (!wrap || !Array.isArray(kpis)) return;

    wrap.innerHTML = kpis
      .map((kpi) => {
        const alertClass = kpi.alert ? " adm-kpi--alert" : "";
        const suffix = kpi.suffix
          ? ` <span class="adm-kpi__suffix">${kpi.suffix}</span>`
          : "";
        return `<article class="adm-kpi adm-kpi--${kpi.id}${alertClass}">
          <div class="adm-kpi__head">
            <span class="adm-kpi__label">${kpi.label}</span>
            <span class="adm-kpi__trend adm-kpi__trend--${kpi.trend}" title="${kpi.hint}">
              ${trendPrefix(kpi.trend)}${Number(kpi.delta_pct || 0).toFixed(1)}%
            </span>
          </div>
          <strong class="adm-kpi__value">${kpi.value_label}${suffix}</strong>
          <span class="adm-kpi__hint">${kpi.hint}</span>
        </article>`;
      })
      .join("");

    kpis.forEach((kpi) => {
      const hero = document.querySelector(`[data-hero-metric="${kpi.id}"] strong`);
      if (hero) hero.textContent = kpi.value_label;
    });

    const reportsKpi = kpis.find((k) => k.id === "reports");
    const reportsCard = document.querySelector("[data-dashboard-recent-reports-wrap]");
    if (reportsCard && reportsKpi?.alert) {
      reportsCard.classList.add("adm-card--alert");
    }

    window.AdmLive?.reveal(wrap);
  }

  function renderRecent(recent) {
    const txBody = document.querySelector("[data-dashboard-recent-tx]");
    const reportsWrap = document.querySelector("[data-dashboard-recent-reports]");
    const txCard = document.querySelector("[data-dashboard-recent-tx-wrap]");
    const reportsCard = document.querySelector("[data-dashboard-recent-reports-wrap]");

    if (txBody) {
      const rows = recent?.transactions || [];
      txBody.innerHTML = rows.length
        ? rows
            .map(
              (tx) => `<tr>
                <td data-label="ID"><code class="adm-plan-id">#${tx.id}</code></td>
                <td data-label="Type">${tx.type}</td>
                <td data-label="Montant"><strong>${tx.amount_label}</strong> FCFA</td>
                <td data-label="Statut"><span class="adm-badge adm-badge--${statusBadgeClass(tx.status)}">${tx.status_label}</span></td>
                <td data-label="Date">${formatDate(tx.created_at)}</td>
              </tr>`
            )
            .join("")
        : '<tr><td colspan="5"><div class="adm-empty">Aucune transaction récente</div></td></tr>';
    }

    if (reportsWrap) {
      const reports = recent?.reports || [];
      reportsWrap.innerHTML = reports.length
        ? reports
            .map(
              (r) => `<article class="adm-mod-item">
                <div class="adm-mod-item__main">
                  <strong>${r.reason}</strong>
                  <p>${r.profile_name} · ${formatDate(r.created_at)}</p>
                </div>
                <span class="adm-badge adm-badge--warn">En attente</span>
              </article>`
            )
            .join("")
        : '<div class="adm-empty">Aucun signalement urgent</div>';
    }

    window.AdmLive?.reveal(txCard);
    window.AdmLive?.reveal(reportsCard);
  }

  function initGeoAllModal(geography) {
    const modal = document.getElementById("adm-geo-modal");
    const openBtn = document.querySelector("[data-geo-all-open]");
    const listBody = document.querySelector("[data-geo-all-list]");
    const summary = document.querySelector("[data-geo-all-summary]");
    if (!modal || !openBtn || !listBody || !geography || !geography.all || !geography.all.length) {
      return;
    }

    openBtn.hidden = false;
    if (summary) {
      summary.textContent = `${geography.country_count || geography.all.length} pays · ${(geography.total || 0).toLocaleString("fr-FR")} membres`;
    }
    listBody.innerHTML = geography.all
      .map(
        (row, index) =>
          `<tr><td>${index + 1}</td><td>${row.country}</td><td><strong>${row.count.toLocaleString("fr-FR")}</strong></td></tr>`
      )
      .join("");

    let lastFocus = null;

    function openModal() {
      lastFocus = document.activeElement;
      modal.hidden = false;
      document.body.classList.add("is-adm-geo-modal");
      const closeBtn = modal.querySelector("[data-geo-all-close]");
      if (closeBtn) closeBtn.focus();
    }

    function closeModal() {
      modal.hidden = true;
      document.body.classList.remove("is-adm-geo-modal");
      if (lastFocus && typeof lastFocus.focus === "function") lastFocus.focus();
    }

    openBtn.addEventListener("click", openModal);
    modal.querySelectorAll("[data-geo-all-close]").forEach((node) => {
      node.addEventListener("click", closeModal);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !modal.hidden) closeModal();
    });
  }

  function initCharts(data) {
    if (typeof Chart === "undefined" || !data) return;

    Chart.defaults.font.family = "'DM Sans', sans-serif";
    Chart.defaults.color = COLORS.bordeaux;

    const gridColor = "rgba(232,99,122,0.08)";
    const axis = {
      x: { grid: { color: gridColor }, ticks: { maxTicksLimit: 10 } },
      y: { beginAtZero: true, grid: { color: gridColor } },
    };

    const revenueCtx = document.getElementById("chart-revenue");
    if (revenueCtx && data.revenue) {
      new Chart(revenueCtx, {
        type: "line",
        data: {
          labels: data.labels,
          datasets: [
            lineDataset("Abonnements", data.revenue.subscription, COLORS.rose),
            lineDataset("Achats à la carte", data.revenue.one_shot, COLORS.vip),
          ],
        },
        options: baseOptions({ scales: axis }),
      });
    }

    const acquisitionCtx = document.getElementById("chart-acquisition");
    if (acquisitionCtx && data.acquisition) {
      new Chart(acquisitionCtx, {
        type: "bar",
        data: {
          labels: data.labels,
          datasets: [
            {
              label: "Nouveaux inscrits",
              data: data.acquisition.signups,
              backgroundColor: COLORS.rose,
              borderRadius: 6,
              borderSkipped: false,
            },
            {
              label: "Comptes bannis",
              data: data.acquisition.churn,
              backgroundColor: COLORS.bordeauxMedium,
              borderRadius: 6,
              borderSkipped: false,
            },
          ],
        },
        options: baseOptions({ scales: { ...axis, x: { ...axis.x, stacked: false } } }),
      });
    }

    function doughnut(id, labels, values) {
      const ctx = document.getElementById(id);
      if (!ctx || !labels.length) return;
      new Chart(ctx, {
        type: "doughnut",
        data: {
          labels,
          datasets: [{
            data: values,
            backgroundColor: PALETTE.slice(0, labels.length),
            borderColor: COLORS.white,
            borderWidth: 2,
            hoverOffset: 6,
          }],
        },
        options: baseOptions({
          cutout: "62%",
          plugins: { legend: { position: "bottom" } },
        }),
      });
    }

    doughnut("chart-gender", data.demographics.gender_labels, data.demographics.gender_values);

    const funnelCtx = document.getElementById("chart-funnel");
    if (funnelCtx && data.funnel) {
      new Chart(funnelCtx, {
        type: "bar",
        data: {
          labels: data.funnel.labels,
          datasets: [{
            label: "Utilisateurs",
            data: data.funnel.values,
            backgroundColor: [COLORS.rose, COLORS.secondary, COLORS.bordeauxMedium, COLORS.vip, COLORS.success],
            borderRadius: 8,
            borderSkipped: false,
          }],
        },
        options: baseOptions({
          indexAxis: "y",
          plugins: { legend: { display: false } },
          scales: {
            x: { beginAtZero: true, grid: { color: gridColor } },
            y: { grid: { display: false } },
          },
        }),
      });
    }

    const geoCtx = document.getElementById("chart-geography");
    if (geoCtx && data.geography && data.geography.labels.length) {
      const geoLabels = data.geography.labels;
      const geoValues = data.geography.values;
      const wrap = geoCtx.closest(".adm-chart-wrap");
      if (wrap) {
        wrap.style.height = `${Math.max(300, geoLabels.length * 44 + 64)}px`;
      }
      const geoCountLabels = geoValues.map((value) => value.toLocaleString("fr-FR"));
      const geoBarLabels = {
        id: "geoBarLabels",
        afterDatasetsDraw(chart) {
          const { ctx, chartArea } = chart;
          const meta = chart.getDatasetMeta(0);
          ctx.save();
          ctx.fillStyle = COLORS.bordeaux;
          ctx.font = "600 12px 'DM Sans', sans-serif";
          ctx.textAlign = "right";
          ctx.textBaseline = "middle";
          meta.data.forEach((bar, index) => {
            ctx.fillText(geoCountLabels[index], chartArea.right - 2, bar.y);
          });
          ctx.restore();
        },
      };
      new Chart(geoCtx, {
        type: "bar",
        data: {
          labels: geoLabels,
          datasets: [{
            label: "Membres",
            data: geoValues,
            backgroundColor: COLORS.rose,
            borderRadius: 8,
            borderSkipped: false,
            maxBarThickness: 26,
            minBarLength: 12,
          }],
        },
        plugins: [geoBarLabels],
        options: baseOptions({
          indexAxis: "y",
          layout: { padding: { right: 8, left: 4 } },
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label(context) {
                  const value = context.parsed.x || 0;
                  return `${value.toLocaleString("fr-FR")} membres`;
                },
              },
            },
          },
          scales: {
            x: {
              beginAtZero: true,
              grid: { color: gridColor },
              ticks: {
                precision: 0,
                color: COLORS.secondary,
                font: { size: 11 },
              },
              border: { display: false },
            },
            y: {
              grid: { display: false },
              border: { display: false },
              ticks: {
                autoSkip: false,
                font: { size: 12, weight: "600" },
                color: COLORS.bordeaux,
                padding: 8,
              },
            },
          },
        }),
      });
    }

    if (data.geography) initGeoAllModal(data.geography);
    window.AdmLive?.reveal(document.querySelector("[data-dashboard-charts]"));
  }

  document.addEventListener("DOMContentLoaded", () => {
    const cfg = document.getElementById("dashboard-async-config");
    const live = window.AdmLive;
    if (!cfg || !live) return;

    Promise.all([
      live.fetchJson(cfg.dataset.kpisUrl).then((payload) => {
        live.applySyncMeta(payload.sync);
        renderKpis(payload.kpis);
      }),
      live.fetchJson(cfg.dataset.recentUrl).then((payload) => renderRecent(payload.recent)),
      live.fetchJson(cfg.dataset.chartsUrl).then((payload) => {
        live.applySyncMeta(payload.sync);
        if (typeof Chart !== "undefined") {
          initCharts(payload.charts);
          return;
        }
        const waitChart = window.setInterval(() => {
          if (typeof Chart !== "undefined") {
            window.clearInterval(waitChart);
            initCharts(payload.charts);
          }
        }, 40);
      }),
    ]).catch(() => {
      const text = document.querySelector("[data-adm-live-text]");
      if (text) text.textContent = "Certaines données n'ont pas pu être chargées.";
    });
  });
})();
