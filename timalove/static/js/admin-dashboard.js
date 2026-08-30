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

  document.addEventListener("DOMContentLoaded", () => {
    if (typeof Chart === "undefined") return;
    const data = readData();
    if (!data) return;

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
      const max = Math.max(...data.geography.values, 1);
      const shades = data.geography.values.map((value) => {
        const ratio = value / max;
        if (ratio > 0.75) return COLORS.rose;
        if (ratio > 0.5) return COLORS.secondary;
        if (ratio > 0.25) return COLORS.bordeauxMedium;
        return COLORS.rosePale;
      });
      new Chart(geoCtx, {
        type: "bar",
        data: {
          labels: data.geography.labels,
          datasets: [{
            label: "Membres",
            data: data.geography.values,
            backgroundColor: shades,
            borderRadius: 6,
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
  });
})();
