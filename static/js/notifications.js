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

  function markReadUrl(template, id) {
    return template.replace(/0\/read\//, id + "/read/");
  }

  function renderDropdown(root, data) {
    var list = qs(".pulse-notif__list", root);
    var badge = qs(".pulse-notif__badge", root);
    if (!list) return;
    var unread = data.unread_count || 0;
    if (badge) {
      if (unread > 0) {
        badge.textContent = unread > 99 ? "99+" : String(unread);
        badge.hidden = false;
        badge.removeAttribute("aria-hidden");
      } else {
        badge.hidden = true;
        badge.setAttribute("aria-hidden", "true");
      }
    }
    var items = data.items || [];
    if (!items.length) {
      list.innerHTML = '<p class="pulse-notif__empty muted">Нет уведомлений</p>';
      return;
    }
    list.innerHTML = items
      .map(function (it) {
        var unreadCls = it.is_read ? "" : " pulse-notif__item--unread";
        var link = it.link || "";
        return (
          '<button type="button" class="pulse-notif__item' +
          unreadCls +
          '" data-id="' +
          it.id +
          '" data-link="' +
          escapeHtml(link) +
          '">' +
          '<span class="pulse-notif__item-msg">' +
          escapeHtml(it.message) +
          "</span>" +
          '<span class="pulse-notif__item-time muted">' +
          escapeHtml(it.time_label || "") +
          "</span></button>"
        );
      })
      .join("");
  }

  window.PulseNotifications = {
    init: function (root) {
      if (!root) return;
      var listUrl = root.dataset.listUrl;
      var markAllUrl = root.dataset.markAllUrl;
      var tpl = root.dataset.markReadTemplate || "";
      var toggle = qs(".pulse-notif__toggle", root);
      var panel = qs(".pulse-notif__dropdown", root);
      var list = qs(".pulse-notif__list", root);
      var markAllBtn = qs(".pulse-notif__mark-all", root);

      if (list) {
        list.addEventListener("click", function (e) {
          var btn = e.target.closest(".pulse-notif__item");
          if (!btn || !list.contains(btn)) return;
          var id = parseInt(btn.getAttribute("data-id"), 10);
          var link = btn.getAttribute("data-link") || "";
          var url = markReadUrl(tpl, id);
          fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: { Accept: "application/json", "X-CSRFToken": getCsrf() },
          }).finally(function () {
            if (link) window.location.href = link;
            else window.location.reload();
          });
        });
      }

      function close() {
        if (panel) {
          panel.hidden = true;
        }
        if (toggle) toggle.setAttribute("aria-expanded", "false");
      }

      function open() {
        if (panel) panel.hidden = false;
        if (toggle) toggle.setAttribute("aria-expanded", "true");
        if (listUrl) {
          fetch(listUrl, { credentials: "same-origin", headers: { Accept: "application/json" } })
            .then(function (r) {
              return r.json();
            })
            .then(function (data) {
              renderDropdown(root, data);
            })
            .catch(function () {});
        }
      }

      if (toggle && panel) {
        toggle.addEventListener("click", function (e) {
          e.stopPropagation();
          if (panel.hidden) open();
          else close();
        });
        document.addEventListener("click", function () {
          close();
        });
        panel.addEventListener("click", function (e) {
          e.stopPropagation();
        });
      }

      if (markAllBtn && markAllUrl && listUrl) {
        markAllBtn.addEventListener("click", function (e) {
          e.preventDefault();
          e.stopPropagation();
          fetch(markAllUrl, {
            method: "POST",
            credentials: "same-origin",
            headers: { Accept: "application/json", "X-CSRFToken": getCsrf() },
          })
            .then(function () {
              return fetch(listUrl, { credentials: "same-origin", headers: { Accept: "application/json" } });
            })
            .then(function (r) {
              return r.json();
            })
            .then(function (data) {
              renderDropdown(root, data);
            })
            .catch(function () {});
        });
      }

      if (panel) {
        panel.hidden = true;
      }
      if (toggle) {
        toggle.setAttribute("aria-expanded", "false");
      }
    },
  };
})(window);
