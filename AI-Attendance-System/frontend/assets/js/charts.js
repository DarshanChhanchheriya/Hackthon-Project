// Chart.js helpers (Chart.js loaded via CDN in each page that needs it).
window.Charts = (() => {
  const palette = ["#2563eb", "#4f8dff", "#16a34a", "#d97706", "#dc2626", "#7c3aed"];

  function gridColor() {
    return getComputedStyle(document.documentElement).getPropertyValue("--border").trim() || "#e6e9ef";
  }
  function textColor() {
    return getComputedStyle(document.documentElement).getPropertyValue("--text-muted").trim() || "#64748b";
  }

  function lineChart(ctx, labels, datasets) {
    return new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: datasets.map((d, i) => ({
          label: d.label,
          data: d.data,
          borderColor: palette[i % palette.length],
          backgroundColor: palette[i % palette.length] + "22",
          tension: 0.4,
          fill: true,
          pointRadius: 0,
          borderWidth: 2.5,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: textColor() } } },
        scales: {
          x: { grid: { color: gridColor() }, ticks: { color: textColor() } },
          y: { grid: { color: gridColor() }, ticks: { color: textColor() } },
        },
      },
    });
  }

  function barChart(ctx, labels, datasets) {
    return new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: datasets.map((d, i) => ({
          label: d.label,
          data: d.data,
          backgroundColor: palette[i % palette.length],
          borderRadius: 8,
          maxBarThickness: 34,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: textColor() } } },
        scales: {
          x: { grid: { display: false }, ticks: { color: textColor() } },
          y: { grid: { color: gridColor() }, ticks: { color: textColor() } },
        },
      },
    });
  }

  function pieChart(ctx, labels, data) {
    return new Chart(ctx, {
      type: "doughnut",
      data: {
        labels,
        datasets: [{ data, backgroundColor: palette, borderWidth: 0, hoverOffset: 8 }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "68%",
        plugins: { legend: { position: "bottom", labels: { color: textColor(), padding: 16 } } },
      },
    });
  }

  return { lineChart, barChart, pieChart, palette };
})();
