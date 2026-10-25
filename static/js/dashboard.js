(function () {
  const el = document.getElementById("dash-data");
  if (!el || typeof Chart === "undefined") return;
  const d = JSON.parse(el.textContent);
  const css = getComputedStyle(document.documentElement);
  const v = n => css.getPropertyValue(n).trim();
  Chart.defaults.font.family = v("--font");
  Chart.defaults.color = v("--muted");
  const grid = { color: v("--line") };

  new Chart(document.getElementById("statusChart"), {
    type: "doughnut",
    data: { labels: ["Good (≥80%)", "Warning (75–79%)", "Critical (<75%)"],
      datasets: [{ data: d.status, backgroundColor: [v("--good"), v("--warn"), v("--crit")], borderColor: v("--surface"), borderWidth: 3 }] },
    options: { maintainAspectRatio: false, cutout: "62%", plugins: { legend: { position: "bottom" } } },
  });

  const colour = x => (x >= 80 ? v("--good") : x >= 75 ? v("--warn") : v("--crit"));
  new Chart(document.getElementById("courseChart"), {
    type: "bar",
    data: { labels: d.course_labels, datasets: [{ label: "Average %", data: d.course_values, backgroundColor: d.course_values.map(colour), borderRadius: 4 }] },
    options: { maintainAspectRatio: false, plugins: { legend: { display: false } },
      scales: { y: { min: 0, max: 100, grid, ticks: { callback: x => x + "%" } }, x: { grid: { display: false } } } },
  });

  new Chart(document.getElementById("trendChart"), {
    type: "line",
    data: { labels: d.trend_labels, datasets: [{ label: "Attendance rate", data: d.trend_values, borderColor: v("--brand"),
      backgroundColor: v("--brand-soft"), fill: true, tension: .3, pointRadius: 3 }] },
    options: { maintainAspectRatio: false, plugins: { legend: { display: false } },
      scales: { y: { min: 0, max: 100, grid, ticks: { callback: x => x + "%" } }, x: { grid: { display: false } } } },
  });
})();
