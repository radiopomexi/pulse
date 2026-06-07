
(function (window) {
  "use strict";

  window.PulseModal = {
    bindPlanModal: function (backdropId, openId, closeId) {
      var backdrop = document.getElementById(backdropId);
      var openBtn = document.getElementById(openId);
      var closeBtn = document.getElementById(closeId);
      if (!backdrop || !openBtn || !closeBtn) return;

      function open() {
        backdrop.classList.add("is-open");
      }
      function close() {
        backdrop.classList.remove("is-open");
      }

      openBtn.addEventListener("click", open);
      closeBtn.addEventListener("click", close);
      backdrop.addEventListener("click", function (e) {
        if (e.target === backdrop) close();
      });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") close();
      });
    },
  };
})(window);
