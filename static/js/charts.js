
(function (window) {
  "use strict";

  var LINE = "#3b82f6";

  var DOUGH_COLORS = [
    "rgba(59, 130, 246, 0.85)",
    "rgba(96, 165, 250, 0.8)",
    "rgba(34, 197, 94, 0.75)",
    "rgba(251, 191, 36, 0.75)",
    "rgba(167, 139, 250, 0.8)",
    "rgba(248, 113, 113, 0.65)",
  ];

  function cssVar(name, fallback) {
    var v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v && v.length ? v : fallback;
  }

  function palette() {
    return {
      grid: cssVar("--chart-grid", "rgba(51, 65, 85, 0.3)"),
      tick: cssVar("--chart-tick", "#94a3b8"),
      ttBg: cssVar("--chart-tooltip-bg", "#112240"),
      ttTitle: cssVar("--chart-tooltip-title", "#e2e8f0"),
      ttBody: cssVar("--chart-tooltip-body", "#94a3b8"),
      ttBorder: cssVar("--chart-tooltip-border", "#334155"),
      pointBorder: cssVar("--chart-point-border", "#f1f5f9"),
    };
  }

  function readJson(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return null;
    }
  }

  function lineGradient(ctx, chartArea) {
    var g = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
    g.addColorStop(0, "rgba(59, 130, 246, 0.15)");
    g.addColorStop(1, "rgba(59, 130, 246, 0)");
    return g;
  }

  function baseOptions() {
    var P = palette();
    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 900, easing: "easeOutQuart" },
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          labels: { color: P.tick, font: { family: "Inter", size: 11 } },
        },
        tooltip: {
          backgroundColor: P.ttBg,
          titleColor: P.ttTitle,
          bodyColor: P.ttBody,
          borderColor: P.ttBorder,
          borderWidth: 1,
        },
      },
      scales: {
        x: {
          ticks: { color: P.tick, font: { family: "Inter", size: 11 } },
          grid: { color: P.grid, drawBorder: false },
        },
        y: {
          ticks: { color: P.tick, font: { family: "Inter", size: 11 } },
          grid: { color: P.grid, drawBorder: false },
        },
      },
    };
  }

  function doughnutOptions() {
    var P = palette();
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: { color: P.tick, font: { family: "Inter", size: 11 } },
        },
        tooltip: {
          backgroundColor: P.ttBg,
          titleColor: P.ttTitle,
          bodyColor: P.ttBody,
          borderColor: P.ttBorder,
          borderWidth: 1,
        },
      },
    };
  }

  /** Только дашборд «Прогресс по упражнениям» (chartDashExercises): без offset по X, Y от min(вес) или 0. */
  function dashExerciseProgressOptions(exw) {
    var exOpts = baseOptions();
    exOpts.scales.x = Object.assign({}, exOpts.scales.x, { offset: false });
    var allVals = [];
    (exw.datasets || []).forEach(function (d) {
      (d.data || []).forEach(function (v) {
        if (v != null && v !== "" && !isNaN(Number(v))) {
          allVals.push(Number(v));
        }
      });
    });
    var yMin = 0;
    if (allVals.length) {
      var vmin = Math.min.apply(null, allVals);
      var vmax = Math.max.apply(null, allVals);
      var span = vmax - vmin;
      var pad = span > 0 ? Math.max(0.5, span * 0.12) : Math.max(0.5, vmin * 0.05 || 1);
      yMin = Math.max(0, Math.round((vmin - pad) * 10) / 10);
    }
    exOpts.scales.y = Object.assign({}, exOpts.scales.y, { min: yMin });
    return exOpts;
  }

  window.PulseCharts = {
    initDashboard: function () {
      var weeks = readJson("pulse-chart-weeks");
      var days = readJson("pulse-chart-days");
      var types = readJson("pulse-dash-types");
      var exw = readJson("pulse-dash-exercises");
      if (weeks && document.getElementById("chartVolumeWeeks")) {
        var ctx = document.getElementById("chartVolumeWeeks").getContext("2d");
        new Chart(ctx, {
          type: "line",
          data: {
            labels: weeks.labels,
            datasets: [
              {
                label: "Тоннаж",
                data: weeks.values,
                borderColor: LINE,
                borderWidth: 2,
                tension: 0.35,
                fill: true,
                backgroundColor: function (context) {
                  var chart = context.chart;
                  var area = chart.chartArea;
                  if (!area) return null;
                  return lineGradient(chart.ctx, area);
                },
                pointRadius: 4,
                pointHoverRadius: 4,
                pointBackgroundColor: LINE,
                pointBorderColor: palette().pointBorder,
                pointBorderWidth: 2,
              },
            ],
          },
          options: baseOptions(),
        });
      }
      if (days && document.getElementById("chartSessionsDays")) {
        var ctx2 = document.getElementById("chartSessionsDays").getContext("2d");
        new Chart(ctx2, {
          type: "bar",
          data: {
            labels: days.labels,
            datasets: [
              {
                label: "Сессии",
                data: days.values,
                backgroundColor: "rgba(59, 130, 246, 0.35)",
                borderColor: LINE,
                borderWidth: 1,
                borderRadius: 6,
              },
            ],
          },
          options: baseOptions(),
        });
      }
      if (types && types.labels && types.labels.length && document.getElementById("chartDashTypes")) {
        var ctx3 = document.getElementById("chartDashTypes").getContext("2d");
        var bg = types.labels.map(function (_, i) {
          return DOUGH_COLORS[i % DOUGH_COLORS.length];
        });
        new Chart(ctx3, {
          type: "doughnut",
          data: {
            labels: types.labels,
            datasets: [
              {
                data: types.values,
                borderWidth: 2,
                borderColor: cssVar("--bg-page", "#0a1628"),
                backgroundColor: bg,
              },
            ],
          },
          options: doughnutOptions(),
        });
      }
      if (exw && exw.datasets && exw.datasets.length && document.getElementById("chartDashExercises")) {
        var ctx4 = document.getElementById("chartDashExercises").getContext("2d");
        var colors = ["#3b82f6", "#60a5fa", "#2563eb", "#93c5fd", "#1d4ed8"];
        var ds = exw.datasets.map(function (d, i) {
          return {
            label: d.label,
            data: d.data,
            borderColor: colors[i % colors.length],
            borderWidth: 2,
            tension: 0.35,
            spanGaps: true,
            fill: false,
            pointRadius: 3,
            pointBorderColor: palette().pointBorder,
            pointBackgroundColor: colors[i % colors.length],
            pointBorderWidth: 1,
          };
        });
        new Chart(ctx4, {
          type: "line",
          data: { labels: exw.labels, datasets: ds },
          options: dashExerciseProgressOptions(exw),
        });
      }
      var bw = readJson("pulse-dash-body-weight");
      var canvasBw = document.getElementById("chartDashBodyWeight");
      if (bw && bw.has_enough && canvasBw) {
        var oldBw = Chart.getChart(canvasBw);
        if (oldBw) oldBw.destroy();
        var vals = (bw.values || []).map(Number).filter(function (x) {
          return !isNaN(x);
        });
        if (vals.length) {
          var vmin = Math.min.apply(null, vals);
          var vmax = Math.max.apply(null, vals);
          var pad = Math.max(0.5, (vmax - vmin) * 0.15 || 1);
          var optsBw = baseOptions();
          optsBw.scales.y.suggestedMin = Math.round((vmin - pad) * 10) / 10;
          optsBw.scales.y.suggestedMax = Math.round((vmax + pad) * 10) / 10;
          var ctxBw = canvasBw.getContext("2d");
          new Chart(ctxBw, {
            type: "line",
            data: {
              labels: bw.labels,
              datasets: [
                {
                  label: "Вес, кг",
                  data: bw.values,
                  borderColor: "#34d399",
                  borderWidth: 2,
                  tension: 0.3,
                  fill: true,
                  backgroundColor: "rgba(52, 211, 153, 0.12)",
                  pointRadius: 4,
                  pointBackgroundColor: "#34d399",
                  pointBorderColor: palette().pointBorder,
                  pointBorderWidth: 2,
                },
              ],
            },
            options: optsBw,
          });
        }
      }
      bindChartResize();
    },

    initProfile: function () {
      var types = readJson("pulse-profile-types");
      var elTypes = document.getElementById("chartProfileTypes");
      if (types && elTypes) {
        var oldT = Chart.getChart(elTypes);
        if (oldT) oldT.destroy();
        var ctx = elTypes.getContext("2d");
        var bg = (types.labels || []).map(function (_, i) {
          return DOUGH_COLORS[i % DOUGH_COLORS.length];
        });
        new Chart(ctx, {
          type: "doughnut",
          data: {
            labels: types.labels,
            datasets: [
              {
                data: types.values,
                borderWidth: 2,
                borderColor: cssVar("--bg-page", "#0a1628"),
                backgroundColor: bg,
              },
            ],
          },
          options: doughnutOptions(),
        });
      }
      var prog = readJson("pulse-profile-exercises");
      var elProg = document.getElementById("chartProfileExercises");
      if (prog && prog.datasets && prog.datasets.length && elProg) {
        var oldP = Chart.getChart(elProg);
        if (oldP) oldP.destroy();
        var ctx2 = elProg.getContext("2d");
        var colors = ["#3b82f6", "#60a5fa", "#2563eb", "#93c5fd", "#1d4ed8"];
        var ds = prog.datasets.map(function (d, i) {
          return {
            label: d.label,
            data: d.data,
            borderColor: colors[i % colors.length],
            borderWidth: 2,
            tension: 0.35,
            spanGaps: true,
            fill: false,
            pointRadius: 3,
            pointBorderColor: palette().pointBorder,
            pointBackgroundColor: colors[i % colors.length],
            pointBorderWidth: 1,
          };
        });
        new Chart(ctx2, {
          type: "line",
          data: { labels: prog.labels, datasets: ds },
          options: baseOptions(),
        });
      }
      bindChartResize();
    },

    initProfileBodyWeight: function () {
      var data = readJson("pulse-profile-body-weight");
      var canvas = document.getElementById("chartBodyWeight");
      if (!data || !data.has_enough || !canvas) return;
      var existing = Chart.getChart(canvas);
      if (existing) existing.destroy();
      var vals = (data.values || []).map(Number).filter(function (x) {
        return !isNaN(x);
      });
      if (!vals.length) return;
      var vmin = Math.min.apply(null, vals);
      var vmax = Math.max.apply(null, vals);
      var pad = Math.max(0.5, (vmax - vmin) * 0.15 || 1);
      var opts = baseOptions();
      opts.scales.y.suggestedMin = Math.round((vmin - pad) * 10) / 10;
      opts.scales.y.suggestedMax = Math.round((vmax + pad) * 10) / 10;
      var ctx = canvas.getContext("2d");
      new Chart(ctx, {
        type: "line",
        data: {
          labels: data.labels,
          datasets: [
            {
              label: "Вес, кг",
              data: data.values,
              borderColor: "#34d399",
              borderWidth: 2,
              tension: 0.3,
              fill: true,
              backgroundColor: "rgba(52, 211, 153, 0.12)",
              pointRadius: 4,
              pointBackgroundColor: "#34d399",
              pointBorderColor: palette().pointBorder,
              pointBorderWidth: 2,
            },
          ],
        },
        options: opts,
      });
      bindChartResize();
    },

    initWeightTrackingPage: function () {
      var data = readJson("pulse-weight-tracking-chart");
      var canvas = document.getElementById("chartWeightPage");
      if (!data || !data.has_enough || !canvas) return;
      var existing = Chart.getChart(canvas);
      if (existing) existing.destroy();
      var vals = (data.values || []).map(Number).filter(function (x) {
        return !isNaN(x);
      });
      if (!vals.length) return;
      var vmin = Math.min.apply(null, vals);
      var vmax = Math.max.apply(null, vals);
      var pad = Math.max(0.5, (vmax - vmin) * 0.15 || 1);
      var opts = baseOptions();
      opts.scales.y.suggestedMin = Math.round((vmin - pad) * 10) / 10;
      opts.scales.y.suggestedMax = Math.round((vmax + pad) * 10) / 10;
      var ctx = canvas.getContext("2d");
      new Chart(ctx, {
        type: "line",
        data: {
          labels: data.labels,
          datasets: [
            {
              label: "Вес, кг",
              data: data.values,
              borderColor: "#34d399",
              borderWidth: 2,
              tension: 0.3,
              fill: true,
              backgroundColor: "rgba(52, 211, 153, 0.12)",
              pointRadius: 4,
              pointBackgroundColor: "#34d399",
              pointBorderColor: palette().pointBorder,
              pointBorderWidth: 2,
            },
          ],
        },
        options: opts,
      });
      bindChartResize();
    },

    refreshForTheme: function () {
      if (typeof Chart === "undefined") return;
      var bo = baseOptions();
      var dopts = doughnutOptions();
      var pb = palette().pointBorder;
      var pageBg = cssVar("--bg-page", "#0a1628");
      chartIds.forEach(function (id) {
        var el = document.getElementById(id);
        if (!el) return;
        var ch = Chart.getChart(el);
        if (!ch) return;
        if (ch.config.type === "doughnut") {
          if (ch.options.plugins.legend && ch.options.plugins.legend.labels) {
            ch.options.plugins.legend.labels.color = dopts.plugins.legend.labels.color;
          }
          var dtt = ch.options.plugins.tooltip;
          if (dtt && dopts.plugins.tooltip) {
            dtt.backgroundColor = dopts.plugins.tooltip.backgroundColor;
            dtt.titleColor = dopts.plugins.tooltip.titleColor;
            dtt.bodyColor = dopts.plugins.tooltip.bodyColor;
            dtt.borderColor = dopts.plugins.tooltip.borderColor;
          }
          if (ch.data.datasets[0]) ch.data.datasets[0].borderColor = pageBg;
        } else {
          if (ch.options.plugins.legend && ch.options.plugins.legend.labels) {
            ch.options.plugins.legend.labels.color = bo.plugins.legend.labels.color;
          }
          var tt = ch.options.plugins.tooltip;
          if (tt && bo.plugins.tooltip) {
            tt.backgroundColor = bo.plugins.tooltip.backgroundColor;
            tt.titleColor = bo.plugins.tooltip.titleColor;
            tt.bodyColor = bo.plugins.tooltip.bodyColor;
            tt.borderColor = bo.plugins.tooltip.borderColor;
          }
          if (ch.options.scales) {
            ["x", "y"].forEach(function (k) {
              if (ch.options.scales[k] && bo.scales[k]) {
                ch.options.scales[k].ticks.color = bo.scales[k].ticks.color;
                ch.options.scales[k].grid.color = bo.scales[k].grid.color;
              }
            });
          }
        }
        ch.data.datasets.forEach(function (ds) {
          if (ds.pointBorderColor) ds.pointBorderColor = pb;
        });
        ch.update();
      });
    },
  };

  var chartIds = [
    "chartVolumeWeeks",
    "chartSessionsDays",
    "chartDashTypes",
    "chartDashExercises",
    "chartDashBodyWeight",
    "chartProfileTypes",
    "chartProfileExercises",
    "chartBodyWeight",
    "chartWeightPage",
  ];

  function resizePulseCharts() {
    if (typeof Chart === "undefined") return;
    chartIds.forEach(function (id) {
      var el = document.getElementById(id);
      if (!el) return;
      var inst = Chart.getChart(el);
      if (inst) inst.resize();
    });
  }

  function bindChartResize() {
    if (window.__pulseChartResizeBound) return;
    window.__pulseChartResizeBound = true;
    window.addEventListener("resize", function () {
      resizePulseCharts();
    });
  }

  document.addEventListener("pulse-theme-changed", function () {
    if (window.PulseCharts && typeof window.PulseCharts.refreshForTheme === "function") {
      window.PulseCharts.refreshForTheme();
    }
  });
})(window);
