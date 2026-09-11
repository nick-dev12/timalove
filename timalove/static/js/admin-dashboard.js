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

  function readData() {
    const node = document.getElementById("admin-charts-data");
    if (!node) return null;
    try {
      return JSON.parse(node.textContent);
    } catch (_err) {
      return null;
    }
  }

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

  document.addEventListener("DOMContentLoaded", () => {
    const data = readData();
    if (data && data.geography) initGeoAllModal(data.geography);
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
      const max = Math.max(...geoValues, 1);
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
  });
})();
