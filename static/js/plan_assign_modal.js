(function (window) {
  "use strict";

  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function getCsrf() {
    var el = document.querySelector("[name=csrfmiddlewaretoken]");
    return el ? el.value : "";
  }

  function escapeHtml(t) {
    if (t == null) return "";
    var d = document.createElement("div");
    d.textContent = String(t);
    return d.innerHTML;
  }

  window.PulsePlanAssignModal = {
    init: function () {
      var openBtn = document.querySelector("[data-plan-assign-open]");
      var backdrop = document.getElementById("plan-assign-backdrop");
      if (!openBtn || !backdrop) return;
      var athletesUrl = backdrop.dataset.athletesUrl;
      var toggleUrl = backdrop.dataset.toggleUrl;
      var listEl = qs("#plan-assign-athletes-list", backdrop);
      var closeEls = backdrop.querySelectorAll("[data-plan-assign-close]");

      function close() {
        backdrop.classList.remove("is-open");
        backdrop.hidden = true;
        backdrop.setAttribute("aria-hidden", "true");
        document.body.style.overflow = "";
      }

      function open() {
        backdrop.hidden = false;
        backdrop.classList.add("is-open");
        backdrop.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";
        listEl.innerHTML = '<p class="muted" style="margin:0;">Загрузка…</p>';
        fetch(athletesUrl, { credentials: "same-origin", headers: { Accept: "application/json" } })
          .then(function (r) {
            if (!r.ok) throw new Error();
            return r.json();
          })
          .then(function (data) {
            renderList(data.athletes || []);
          })
          .catch(function () {
            listEl.innerHTML = '<p class="message message--error" style="margin:0;">Не удалось загрузить список.</p>';
          });
      }

      function renderList(athletes) {
        if (!athletes.length) {
          listEl.innerHTML = '<p class="muted" style="margin:0;">Нет подтверждённых подопечных. Добавьте связь в профиле.</p>';
          return;
        }
        var rows = athletes.map(function (a) {
          var assigned = a.assigned;
          var btnLabel = assigned ? "Снять" : "Назначить";
          var btnClass = assigned ? "btn btn--ghost btn--sm" : "btn btn--primary btn--sm";
          var status = assigned
            ? '<span class="plan-assign-row__ok" aria-hidden="true">✓</span> <span class="muted">Назначен</span>'
            : '<span class="muted">—</span>';
          return (
            '<tr class="plan-assign-row">' +
            "<td>" +
            escapeHtml(a.name) +
            '<div class="muted" style="font-size:0.8rem;">' +
            escapeHtml(a.email) +
            "</div></td>" +
            "<td>" +
            status +
            "</td>" +
            '<td style="text-align:right;"><button type="button" class="' +
            btnClass +
            '" data-athlete-id="' +
            a.id +
            '" data-assign="' +
            (assigned ? "0" : "1") +
            '">' +
            btnLabel +
            "</button></td></tr>"
          );
        });
        listEl.innerHTML =
          '<table class="plan-assign-table"><thead><tr><th>Спортсмен</th><th>Статус</th><th></th></tr></thead><tbody>' +
          rows.join("") +
          "</tbody></table>";
      }

      openBtn.addEventListener("click", open);
      closeEls.forEach(function (el) {
        el.addEventListener("click", close);
      });
      backdrop.addEventListener("click", function (e) {
        if (e.target === backdrop) close();
      });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && backdrop.classList.contains("is-open")) close();
      });

      listEl.addEventListener("click", function (e) {
        var btn = e.target.closest("button[data-athlete-id]");
        if (!btn) return;
        var athleteId = parseInt(btn.getAttribute("data-athlete-id"), 10);
        var assign = btn.getAttribute("data-assign") === "1";
        btn.disabled = true;
        fetch(toggleUrl, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            "X-CSRFToken": getCsrf(),
          },
          body: JSON.stringify({ athlete_id: athleteId, assign: assign }),
        })
          .then(function (r) {
            return r.json().then(function (j) {
              return { ok: r.ok, body: j };
            });
          })
          .then(function (res) {
            btn.disabled = false;
            if (!res.ok || !res.body.ok) return;
            close();
            window.location.reload();
          })
          .catch(function () {
            btn.disabled = false;
          });
      });
    },
  };
})(window);
