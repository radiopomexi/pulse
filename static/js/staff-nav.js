
(function () {
  "use strict";
  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("staff-menu-toggle");
    var side = document.getElementById("staff-sidebar");
    if (!btn || !side) return;
    btn.addEventListener("click", function () {
      var open = side.classList.toggle("staff-sidebar--open");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
  });
})();
