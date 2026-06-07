(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    var openMenu = null;

    function closeAllMenus() {
      document.querySelectorAll(".staff-dd.is-open").forEach(function (w) {
        w.classList.remove("is-open");
        var b = w.querySelector(".staff-dd__btn");
        var m = w.querySelector(".staff-dd__menu");
        if (b) b.setAttribute("aria-expanded", "false");
        if (m) m.hidden = true;
      });
      openMenu = null;
    }

    document.addEventListener("click", function (e) {
      if (!e.target.closest(".staff-dd")) closeAllMenus();
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeAllMenus();
    });

    document.querySelectorAll("[data-staff-dd]").forEach(function (wrap) {
      var btn = wrap.querySelector(".staff-dd__btn");
      var menu = wrap.querySelector(".staff-dd__menu");
      if (!btn || !menu) return;
      btn.addEventListener("click", function (ev) {
        ev.stopPropagation();
        var isThis = wrap.classList.contains("is-open");
        closeAllMenus();
        if (!isThis) {
          wrap.classList.add("is-open");
          btn.setAttribute("aria-expanded", "true");
          menu.hidden = false;
          openMenu = wrap;
        }
      });
    });

    var dlg = document.getElementById("staff-role-dialog");
    var form = document.getElementById("staff-role-dialog-form");
    var uidField = document.getElementById("staff-role-target-id");
    var sel = document.getElementById("staff-role-select");
    var cancel = document.getElementById("staff-role-dialog-cancel");

    document.querySelectorAll("[data-role-modal-open]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        closeAllMenus();
        if (!dlg || !form || !uidField || !sel) return;
        uidField.value = btn.getAttribute("data-user-id") || "";
        var r = btn.getAttribute("data-role") || "";
        sel.value = r;
        if (dlg.showModal) dlg.showModal();
        else dlg.setAttribute("open", "");
      });
    });
    if (cancel && dlg) cancel.addEventListener("click", function () { dlg.close(); });
  });
})();
