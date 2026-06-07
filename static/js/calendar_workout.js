(function (window) {
  "use strict";

  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function getCsrf() {
    var el = qs("[name=csrfmiddlewaretoken]");
    return el ? el.value : "";
  }

  function buildExerciseSelect(catalog) {
    var parts = ['<option value="">— выберите —</option>'];
    (catalog || []).forEach(function (ex) {
      parts.push('<option value="' + ex.id + '">' + escapeHtml(ex.name) + "</option>");
    });
    return parts.join("");
  }

  function escapeHtml(t) {
    if (t == null) return "";
    var d = document.createElement("div");
    d.textContent = String(t);
    return d.innerHTML;
  }

  function fillWorkoutTypeSelect(select, choices, current) {
    if (!select) return;
    select.innerHTML = "";
    var blank = document.createElement("option");
    blank.value = "";
    blank.textContent = "— не указано —";
    select.appendChild(blank);
    (choices || []).forEach(function (c) {
      var opt = document.createElement("option");
      opt.value = c.value;
      opt.textContent = c.label;
      select.appendChild(opt);
    });
    if (current != null && current !== "") {
      select.value = current;
      if (select.value !== current) select.value = "";
    } else {
      select.value = "";
    }
  }

  var state = {
    urls: {},
    backdrop: null,
    currentIso: null,
    catalogHtml: "",
    planDirty: false,
    suppressPlanChange: false,
    workoutTypeChoices: [],
    pendingPlanId: null,
  };

  function closeModal() {
    if (!state.backdrop) return;
    state.backdrop.classList.remove("is-open");
    state.backdrop.hidden = true;
    state.backdrop.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }

  function openModal() {
    if (!state.backdrop) return;
    state.backdrop.hidden = false;
    state.backdrop.classList.add("is-open");
    state.backdrop.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }

  function rowFromTemplate(tpl, catalogHtml) {
    var node = tpl.content.cloneNode(true);
    var row = node.querySelector(".exercise-row");
    var sel = row.querySelector(".cw-exercise-select");
    if (sel) sel.innerHTML = catalogHtml;
    return row;
  }

  function clearExerciseRows(container, tpl, catalogHtml) {
    container.innerHTML = "";
    container.appendChild(rowFromTemplate(tpl, catalogHtml));
  }

  function collectExercises(container) {
    var out = [];
    container.querySelectorAll(".exercise-row").forEach(function (row) {
      var sel = row.querySelector(".cw-exercise-select");
      var eid = sel && sel.value ? parseInt(sel.value, 10) : NaN;
      if (!eid) return;
      var sets = parseInt(row.querySelector(".cw-in-sets").value, 10) || 1;
      var reps = parseInt(row.querySelector(".cw-in-reps").value, 10) || 1;
      var w = parseFloat(String(row.querySelector(".cw-in-weight").value).replace(",", ".")) || 0;
      out.push({ exercise_id: eid, sets: sets, reps: reps, weight_kg: w });
    });
    return out;
  }

  function setRowsFromData(container, tpl, catalogHtml, rows) {
    container.innerHTML = "";
    if (!rows || !rows.length) {
      container.appendChild(rowFromTemplate(tpl, catalogHtml));
      return;
    }
    rows.forEach(function (r) {
      var row = rowFromTemplate(tpl, catalogHtml);
      var sel = row.querySelector(".cw-exercise-select");
      if (sel) sel.value = String(r.exercise_id);
      row.querySelector(".cw-in-sets").value = String(r.sets != null ? r.sets : 3);
      row.querySelector(".cw-in-reps").value = String(r.reps != null ? r.reps : 10);
      row.querySelector(".cw-in-weight").value =
        r.weight_kg != null && r.weight_kg !== "" ? String(r.weight_kg) : "0";
      container.appendChild(row);
    });
  }

  /** Только строки из PlanExercise: без дефолтных подстановок и без лишней строки. */
  function setRowsFromPlanExercises(container, tpl, catalogHtml, rows) {
    container.innerHTML = "";
    (rows || []).forEach(function (r) {
      var row = rowFromTemplate(tpl, catalogHtml);
      var sel = row.querySelector(".cw-exercise-select");
      if (sel) sel.value = String(r.exercise_id);
      var setsIn = row.querySelector(".cw-in-sets");
      var repsIn = row.querySelector(".cw-in-reps");
      var win = row.querySelector(".cw-in-weight");
      if (setsIn) setsIn.value = r.sets != null && r.sets !== "" ? String(r.sets) : "";
      if (repsIn) repsIn.value = r.reps != null && r.reps !== "" ? String(r.reps) : "";
      if (win) {
        if (r.weight_kg != null && r.weight_kg !== "") win.value = String(r.weight_kg);
        else win.value = "";
      }
      container.appendChild(row);
    });
  }

  function setLinkedPlanLabel(text) {
    var el = qs("#cw-linked-plan-display", state.backdrop);
    if (!el) return;
    if (!text) {
      el.hidden = true;
      el.textContent = "";
      return;
    }
    el.textContent = "План: " + text;
    el.hidden = false;
  }

  function syncLinkedPlanLabelFromSelect() {
    var planSelect = qs("#cw-plan-select", state.backdrop);
    if (!planSelect) return;
    var opt = planSelect.options[planSelect.selectedIndex];
    if (!opt || !opt.value) {
      setLinkedPlanLabel("");
      return;
    }
    setLinkedPlanLabel(opt.textContent || "");
  }

  function planDataUrl(planId) {
    var t = state.urls.planDataTemplate || "";
    return t.replace(/\/0\//, "/" + planId + "/");
  }

  function loadPlanData(planId) {
    return fetch(planDataUrl(planId), { credentials: "same-origin", headers: { Accept: "application/json" } }).then(function (r) {
      if (!r.ok) throw new Error("plan data");
      return r.json();
    });
  }

  function applyStrictPlanDataFromApi(data) {
    var container = qs("#cw-exercise-rows");
    var tpl = qs("#cw-exercise-row-template");
    if (!state.backdrop || !container || !tpl) return;
    container.innerHTML = "";
    setRowsFromPlanExercises(container, tpl, state.catalogHtml, data.exercises || []);
    var choices = state.workoutTypeChoices && state.workoutTypeChoices.length ? state.workoutTypeChoices : CW_FALLBACK_WORKOUT_TYPES;
    var wt = data.workout_type;
    fillWorkoutTypeSelect(qs("#cw-workout-type", state.backdrop), choices, wt != null && wt !== "" ? wt : "");
    var dur = qs("#cw-duration", state.backdrop);
    if (dur) dur.value = data.duration_minutes != null && data.duration_minutes !== "" ? String(data.duration_minutes) : "";
    var notesEl = qs("#cw-notes", state.backdrop);
    if (notesEl) {
      var d = data.description != null ? String(data.description).trim() : "";
      notesEl.value = d;
    }
    setLinkedPlanLabel(data.plan_name || "");
  }

  function wireExerciseRows(container, tpl) {
    container.addEventListener("click", function (e) {
      if (!e.target.closest(".cw-remove-row")) return;
      var row = e.target.closest(".exercise-row");
      if (!row || !container.contains(row)) return;
      var all = container.querySelectorAll(".exercise-row");
      if (all.length <= 1) {
        row.querySelector(".cw-exercise-select").value = "";
        row.querySelector(".cw-in-sets").value = "3";
        row.querySelector(".cw-in-reps").value = "10";
        row.querySelector(".cw-in-weight").value = "0";
        return;
      }
      row.remove();
    });
  }

  function loadDay(iso) {
    var url = state.urls.day + "?date=" + encodeURIComponent(iso);
    return fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } }).then(function (r) {
      if (!r.ok) throw new Error("day");
      return r.json();
    });
  }

  function showDayDetail(iso, dayData) {
    var panel = document.getElementById("day-detail");
    var title = document.getElementById("day-detail-title");
    var list = document.getElementById("day-detail-list");
    var ph = document.getElementById("day-detail-placeholder");
    if (!panel || !title || !list || !ph) return;
    var sessions = (dayData && dayData.sessions) || [];
    var plans = (dayData && dayData.plans) || [];
    if (!iso) {
      panel.hidden = true;
      ph.hidden = false;
      return;
    }
    ph.hidden = true;
    panel.hidden = false;
    title.textContent = iso;
    list.innerHTML = "";
    if (!sessions.length && !plans.length) {
      var li0 = document.createElement("li");
      li0.className = "muted";
      li0.textContent = "Нет тренировок и планов на этот день.";
      list.appendChild(li0);
      return;
    }
    plans.forEach(function (p) {
      var li = document.createElement("li");
      li.className = "session-item";
      li.innerHTML =
        "<strong>План: " +
        escapeHtml(p.name || "План") +
        "</strong>" +
        '<div class="muted" style="font-size:0.8rem;margin-top:4px;">Назначенный план (активен на дату)</div>';
      list.appendChild(li);
    });
    sessions.forEach(function (s) {
      var li = document.createElement("li");
      li.className = "session-item";
      var parts = [];
      parts.push("<strong>" + escapeHtml(s.title || "Тренировка") + "</strong>");
      var meta = [];
      if (s.workout_type) meta.push(escapeHtml(s.workout_type));
      if (s.exercise_count != null) meta.push("упражнений: " + s.exercise_count);
      if (s.tonnage != null) meta.push("тоннаж: " + s.tonnage + " кг×повт");
      if (s.duration) meta.push(s.duration + " мин");
      li.innerHTML =
        parts.join("") +
        '<div class="muted" style="font-size:0.8rem;margin-top:4px;">' +
        meta.join(" · ") +
        "</div>";
      list.appendChild(li);
    });
  }

  var CW_FALLBACK_WORKOUT_TYPES = [
    { value: "strength", label: "Сила" },
    { value: "cardio", label: "Кардио" },
    { value: "flexibility", label: "Гибкость" },
    { value: "circuit", label: "Круговая" },
    { value: "other", label: "Другое" },
  ];

  function calendarReloadUrl(iso) {
    var root = document.getElementById("calendar-app");
    var y = root && root.dataset.year ? root.dataset.year : "";
    var m = root && root.dataset.month ? root.dataset.month : "";
    var u = new URL(window.location.pathname + window.location.search, window.location.origin);
    if (y) u.searchParams.set("year", y);
    if (m) u.searchParams.set("month", m);
    if (iso) u.searchParams.set("open", iso);
    return u.pathname + u.search;
  }

  window.PulseCalendarWorkout = {
    init: function (opts) {
      state.urls.day = opts.dayUrl;
      state.urls.save = opts.saveUrl;
      state.urls.planDataTemplate = opts.planDataUrlTemplate || "";
      state.backdrop = qs(opts.backdrop || "#calendar-workout-backdrop");
      var tpl = qs("#cw-exercise-row-template");
      var container = qs("#cw-exercise-rows");
      if (!state.backdrop || !tpl || !container) return;

      wireExerciseRows(container, tpl);

      state.backdrop.addEventListener("click", function (e) {
        if (e.target === state.backdrop) closeModal();
      });
      var closeBtn = qs(".cw-modal-close", state.backdrop);
      if (closeBtn) closeBtn.addEventListener("click", closeModal);
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && state.backdrop.classList.contains("is-open")) closeModal();
      });

      var planSelect = qs("#cw-plan-select", state.backdrop);
      planSelect.addEventListener("change", function () {
        if (state.suppressPlanChange) return;
        state.planDirty = true;
        var opt = planSelect.options[planSelect.selectedIndex];
        var planId = opt && opt.dataset ? opt.dataset.planId : "";
        if (!planId) {
          setLinkedPlanLabel("");
          return;
        }
        loadPlanData(planId)
          .then(function (data) {
            applyStrictPlanDataFromApi(data);
          })
          .catch(function () {});
      });

      qs("#cw-add-exercise", state.backdrop).addEventListener("click", function () {
        container.appendChild(rowFromTemplate(tpl, state.catalogHtml));
      });

      qs("#cw-save", state.backdrop).addEventListener("click", function () {
        var errEl = qs("#cw-form-error", state.backdrop);
        var title = qs("#cw-title", state.backdrop).value.trim();
        var notes = qs("#cw-notes", state.backdrop).value;
        var duration = qs("#cw-duration", state.backdrop).value.trim();
        var workoutType = qs("#cw-workout-type", state.backdrop).value;
        var exercises = collectExercises(container);
        if (!exercises.length) {
          errEl.textContent = "Добавьте хотя бы одно упражнение.";
          errEl.hidden = false;
          return;
        }
        errEl.textContent = "";
        errEl.hidden = true;
        var planSelectEl = qs("#cw-plan-select", state.backdrop);
        var selVal = planSelectEl.value.trim();
        var payload = {
          date: state.currentIso,
          title: title,
          notes: notes,
          duration_minutes: duration === "" ? null : duration,
          workout_type: workoutType,
          exercises: exercises,
        };
        if (selVal) payload.plan_assignment_id = parseInt(selVal, 10);
        if (state.planDirty && !selVal) payload.clear_plan = true;
        fetch(state.urls.save, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            "X-CSRFToken": getCsrf(),
          },
          body: JSON.stringify(payload),
        })
          .then(function (r) {
            return r.json().then(function (j) {
              return { ok: r.ok, body: j };
            });
          })
          .then(function (res) {
            if (!res.ok || !res.body.ok) {
              errEl.textContent = res.body.error || "Не удалось сохранить.";
              errEl.hidden = false;
              return;
            }
            window.location.href = calendarReloadUrl(state.currentIso);
          })
          .catch(function () {
            errEl.textContent = "Ошибка сети.";
            errEl.hidden = false;
          });
      });
    },

    open: function (iso) {
      if (!state.backdrop || !iso) return;
      state.currentIso = iso;
      state.planDirty = false;
      state.suppressPlanChange = true;
      var container = qs("#cw-exercise-rows");
      var tpl = qs("#cw-exercise-row-template");
      var planSelect = qs("#cw-plan-select", state.backdrop);
      var dateEl = qs("#cw-session-date", state.backdrop);
      var errEl = qs("#cw-form-error", state.backdrop);
      dateEl.textContent = iso;
      errEl.textContent = "";
      errEl.hidden = true;
      setLinkedPlanLabel("");

      state.catalogHtml = state.catalogHtml || buildExerciseSelect([]);
      if (container && tpl) {
        clearExerciseRows(container, tpl, state.catalogHtml);
      }
      if (state.workoutTypeChoices && state.workoutTypeChoices.length) {
        fillWorkoutTypeSelect(qs("#cw-workout-type", state.backdrop), state.workoutTypeChoices, "strength");
      } else {
        fillWorkoutTypeSelect(qs("#cw-workout-type", state.backdrop), CW_FALLBACK_WORKOUT_TYPES, "strength");
      }
      planSelect.innerHTML = '<option value="">— не по плану —</option>';
      qs("#cw-title", state.backdrop).value = "";
      qs("#cw-notes", state.backdrop).value = "";
      qs("#cw-duration", state.backdrop).value = "";

      openModal();

      loadDay(iso)
        .then(function (data) {
          state.catalogHtml = buildExerciseSelect(data.exercise_catalog || []);
          state.workoutTypeChoices = data.workout_type_choices || [];

          planSelect.innerHTML = '<option value="">— не по плану —</option>';
          (data.active_assignments || []).forEach(function (a) {
            var opt = document.createElement("option");
            opt.value = String(a.assignment_id);
            opt.dataset.planId = String(a.plan_id);
            opt.textContent = a.name;
            planSelect.appendChild(opt);
          });

          var sess = data.session;
          if (sess) {
            qs("#cw-title", state.backdrop).value = sess.title || "";
            qs("#cw-notes", state.backdrop).value = sess.notes || "";
            qs("#cw-duration", state.backdrop).value =
              sess.duration_minutes != null ? String(sess.duration_minutes) : "";
            fillWorkoutTypeSelect(qs("#cw-workout-type", state.backdrop), state.workoutTypeChoices, sess.workout_type);
            if (sess.linked_assignment_id) {
              planSelect.value = String(sess.linked_assignment_id);
            } else {
              planSelect.value = "";
            }
            setRowsFromData(container, tpl, state.catalogHtml, sess.exercises || []);
            syncLinkedPlanLabelFromSelect();
          } else {
            qs("#cw-title", state.backdrop).value = "";
            qs("#cw-notes", state.backdrop).value = "";
            qs("#cw-duration", state.backdrop).value = "";
            fillWorkoutTypeSelect(qs("#cw-workout-type", state.backdrop), state.workoutTypeChoices, "strength");
            planSelect.value = "";
            setLinkedPlanLabel("");
            clearExerciseRows(container, tpl, state.catalogHtml);
          }
          var next = Promise.resolve();
          if (state.pendingPlanId) {
            var pid = state.pendingPlanId;
            state.pendingPlanId = null;
            var matchedOpt = null;
            for (var i = 0; i < planSelect.options.length; i++) {
              var o = planSelect.options[i];
              if (o.dataset && String(o.dataset.planId) === String(pid)) {
                matchedOpt = o;
                break;
              }
            }
            if (matchedOpt) {
              planSelect.value = matchedOpt.value;
              syncLinkedPlanLabelFromSelect();
              state.suppressPlanChange = true;
              next = loadPlanData(pid)
                .then(function (pd) {
                  applyStrictPlanDataFromApi(pd);
                })
                .catch(function () {})
                .then(function () {
                  state.suppressPlanChange = false;
                });
            }
          }
          return next;
        })
        .then(function () {
          state.planDirty = false;
          state.suppressPlanChange = false;
          errEl.textContent = "";
          errEl.hidden = true;
        })
        .catch(function () {
          state.suppressPlanChange = false;
          errEl.textContent = "";
          errEl.hidden = true;
        });
    },

    showDayDetail: showDayDetail,
    setPendingPlanId: function (id) {
      state.pendingPlanId = id != null && String(id).trim() !== "" ? String(id).trim() : null;
    },
  };
})(window);
