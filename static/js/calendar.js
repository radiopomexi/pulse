
(function (window) {
  "use strict";

  var WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

  
  function daysInMonth(year, month) {
    return new Date(year, month, 0).getDate();
  }

  function mondayOffset(jsWeekday) {
    return (jsWeekday + 6) % 7;
  }

  function buildMonthMatrix(year, month) {
    var first = new Date(year, month - 1, 1);
    var dim = daysInMonth(year, month);
    var leading = mondayOffset(first.getDay());
    var cells = [];
    var i;
    for (i = 0; i < leading; i++) {
      cells.push({ muted: true, label: "" });
    }
    for (i = 1; i <= dim; i++) {
      cells.push({ muted: false, day: i, label: String(i) });
    }
    while (cells.length % 7 !== 0) {
      cells.push({ muted: true, label: "" });
    }
    while (cells.length < 42) {
      cells.push({ muted: true, label: "" });
    }
    return cells;
  }

  function isoDate(year, month, day) {
    var m = String(month).padStart(2, "0");
    var d = String(day).padStart(2, "0");
    return year + "-" + m + "-" + d;
  }

  window.PulseCalendar = {
    renderMini: function (root, payload, detailEl) {
      if (!root || !payload) return;
      root.classList.add("calendar-root--mini");
      var y = payload.year;
      var m = payload.month;
      var today = payload.today || {};
      var mark = {};
      (payload.daysWithWorkouts || []).forEach(function (d) {
        mark[d] = true;
      });
      var details = payload.dayDetails || {};

      function calNavUrl(newY, newM) {
        var u = new URL(window.location.href);
        u.searchParams.set("cal_year", String(newY));
        u.searchParams.set("cal_month", String(newM));
        if (u.pathname === "/" || u.pathname === "") {
          u.hash = "pulse-home-dashboard";
        }
        return u.toString();
      }

      function shiftMonth(delta) {
        var ny = y;
        var nm = m + delta;
        if (nm > 12) {
          nm = 1;
          ny += 1;
        }
        if (nm < 1) {
          nm = 12;
          ny -= 1;
        }
        window.location.href = calNavUrl(ny, nm);
      }

      function showDayDetail(dayNum) {
        if (!detailEl) return;
        detailEl.removeAttribute("hidden");
        var iso = isoDate(y, m, dayNum);
        var sessions = details[iso] || [];
        if (!sessions.length) {
          detailEl.innerHTML = '<p class="mini-cal-detail__empty muted">Нет тренировок</p>';
          return;
        }
        var parts = [];
        parts.push('<ul class="mini-cal-detail__sessions">');
        sessions.forEach(function (s) {
          parts.push('<li class="mini-cal-detail__session">');
          parts.push('<div class="mini-cal-detail__session-title">' + escapeHtml(s.title || "Тренировка") + "</div>");
          parts.push('<div class="mini-cal-detail__meta muted">');
          parts.push(escapeHtml(s.workout_type || "—"));
          parts.push(" · ");
          parts.push(String(s.exercise_count != null ? s.exercise_count : 0));
          parts.push(" упр. · ");
          parts.push(String(s.tonnage != null ? s.tonnage : "0"));
          parts.push(" кг×повт");
          parts.push("</div>");
          parts.push('<div class="mini-cal-detail__ex muted">');
          parts.push("<span class=\"mini-cal-detail__ex-label\">Упражнения:</span> ");
          parts.push(escapeHtml(s.exercises || "—"));
          parts.push("</div>");
          parts.push("</li>");
        });
        parts.push("</ul>");
        detailEl.innerHTML = parts.join("");
      }

      function escapeHtml(t) {
        if (t == null) return "";
        var d = document.createElement("div");
        d.textContent = String(t);
        return d.innerHTML;
      }

      root.innerHTML = "";
      var toolbar = document.createElement("div");
      toolbar.className = "calendar-toolbar calendar-toolbar--mini";
      var label = document.createElement("div");
      label.className = "calendar-month-label";
      label.textContent = String(m).padStart(2, "0") + " · " + y;
      var nav = document.createElement("div");
      nav.className = "calendar-toolbar__nav";
      var prev = document.createElement("button");
      prev.type = "button";
      prev.className = "btn btn--ghost btn--sm";
      prev.textContent = "<";
      prev.setAttribute("aria-label", "Предыдущий месяц");
      prev.addEventListener("click", function () {
        shiftMonth(-1);
      });
      var next = document.createElement("button");
      next.type = "button";
      next.className = "btn btn--ghost btn--sm";
      next.textContent = ">";
      next.setAttribute("aria-label", "Следующий месяц");
      next.addEventListener("click", function () {
        shiftMonth(1);
      });
      nav.appendChild(prev);
      nav.appendChild(next);
      toolbar.appendChild(label);
      toolbar.appendChild(nav);
      root.appendChild(toolbar);

      var wd = document.createElement("div");
      wd.className = "calendar-weekdays";
      WEEKDAYS.forEach(function (w) {
        var c = document.createElement("div");
        c.textContent = w;
        wd.appendChild(c);
      });
      root.appendChild(wd);

      var cells = buildMonthMatrix(y, m);
      var grid = document.createElement("div");
      grid.className = "calendar-grid";
      cells.forEach(function (cell) {
        var el = document.createElement("button");
        el.type = "button";
        el.className = "cal-cell";
        if (cell.muted) {
          el.classList.add("cal-cell--muted");
          el.textContent = cell.label || "";
          el.disabled = true;
        } else {
          el.textContent = cell.label;
          if (mark[cell.day]) el.classList.add("cal-cell--has-workout");
          if (cell.day === today.d && m === today.m && y === today.y) {
            el.classList.add("cal-cell--today");
          }
          var dayNum = cell.day;
          el.addEventListener("click", function () {
            showDayDetail(dayNum);
          });
        }
        grid.appendChild(el);
      });
      root.appendChild(grid);
    },

    renderFull: function (root, events, options) {
      if (!root) return;
      var year = parseInt(root.dataset.year, 10);
      var month = parseInt(root.dataset.month, 10);
      if (!year || !month) {
        var now = new Date();
        year = now.getFullYear();
        month = now.getMonth() + 1;
      }
      var map = {};
      (events || []).forEach(function (entry) {
        map[entry.date] = entry;
      });
      var onSelect = (options && options.onSelectDay) || function () {};

      function render() {
        root.innerHTML = "";
        var toolbar = document.createElement("div");
        toolbar.className = "calendar-toolbar";
        var label = document.createElement("div");
        label.className = "calendar-month-label";
        label.textContent = String(month).padStart(2, "0") + " · " + year;
        var nav = document.createElement("div");
        nav.style.display = "flex";
        nav.style.gap = "8px";
        function shift(delta) {
          month += delta;
          if (month > 12) {
            month = 1;
            year += 1;
          }
          if (month < 1) {
            month = 12;
            year -= 1;
          }
          var url = new URL(window.location.href);
          url.searchParams.set("year", year);
          url.searchParams.set("month", month);
          window.location.href = url.toString();
        }
        var prev = document.createElement("button");
        prev.type = "button";
        prev.className = "btn btn--ghost btn--sm";
        prev.textContent = "<";
        prev.setAttribute("aria-label", "Предыдущий месяц");
        prev.addEventListener("click", function () {
          shift(-1);
        });
        var next = document.createElement("button");
        next.type = "button";
        next.className = "btn btn--ghost btn--sm";
        next.textContent = ">";
        next.setAttribute("aria-label", "Следующий месяц");
        next.addEventListener("click", function () {
          shift(1);
        });
        nav.appendChild(prev);
        nav.appendChild(next);
        toolbar.appendChild(label);
        toolbar.appendChild(nav);
        root.appendChild(toolbar);

        var wd = document.createElement("div");
        wd.className = "calendar-weekdays";
        WEEKDAYS.forEach(function (w) {
          var c = document.createElement("div");
          c.textContent = w;
          wd.appendChild(c);
        });
        root.appendChild(wd);

        var cells = buildMonthMatrix(year, month);
        var grid = document.createElement("div");
        grid.className = "calendar-grid";
        var today = new Date();
        cells.forEach(function (cell) {
          var el = document.createElement("button");
          el.type = "button";
          el.className = "cal-cell";
          if (cell.muted) {
            el.classList.add("cal-cell--muted");
            el.textContent = cell.label || "·";
            el.disabled = true;
          } else {
            el.textContent = cell.label;
            var iso = isoDate(year, month, cell.day);
            var dayData = map[iso];
            var hasSessions = dayData && dayData.sessions && dayData.sessions.length;
            var hasPlans = dayData && dayData.plans && dayData.plans.length;
            if (hasSessions || hasPlans) {
              el.classList.add("cal-cell--has-workout");
            }
            if (
              cell.day === today.getDate() &&
              month === today.getMonth() + 1 &&
              year === today.getFullYear()
            ) {
              el.classList.add("cal-cell--today");
            }
            el.addEventListener("click", function () {
              onSelect(iso, dayData || { sessions: [], plans: [] });
            });
          }
          grid.appendChild(el);
        });
        root.appendChild(grid);
      }

      render();
    },
  };
})(window);
