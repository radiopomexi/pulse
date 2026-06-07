
(function () {
  "use strict";
  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("nav-toggle");
    var nav = document.getElementById("main-nav");
    if (!btn || !nav) return;
    btn.addEventListener("click", function () {
      var open = nav.classList.toggle("shell__nav--open");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
  });
})();
