(function () {
  "use strict";

  var STORAGE_KEY = "pulse-theme";

  function isLight() {
    return document.documentElement.getAttribute("data-theme") === "light";
  }

  function applyTheme(mode) {
    if (mode === "light") {
      document.documentElement.setAttribute("data-theme", "light");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
    try {
      localStorage.setItem(STORAGE_KEY, mode);
    } catch (e) {}
    window.dispatchEvent(new CustomEvent("pulse-theme-changed"));
  }

  function syncToggleButton(btn) {
    if (!btn) return;
    if (isLight()) {
      btn.setAttribute("aria-label", "Включить тёмную тему");
      btn.setAttribute("title", "Тёмная тема");
    } else {
      btn.setAttribute("aria-label", "Включить светлую тему");
      btn.setAttribute("title", "Светлая тема");
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("theme-toggle");
    syncToggleButton(btn);
    if (!btn) return;
    btn.addEventListener("click", function () {
      applyTheme(isLight() ? "dark" : "light");
      syncToggleButton(btn);
    });
  });
})();
