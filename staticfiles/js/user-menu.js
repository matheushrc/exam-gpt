/* Sidebar-footer user menu: appearance (variant/mode) switches. Depends on
   window.PGTheme (theme.js). */
(function () {
  "use strict";

  function setupUserMenu() {
    var footerBtn = document.getElementById("sidebar-footer");
    var menu = document.getElementById("user-menu");
    if (!menu) {
      return;
    }
    var variantButtons = document.querySelectorAll(".variant-item");
    var modeButtons = document.querySelectorAll(".mode-btn");
    var modeThumb = document.getElementById("mode-thumb");

    function renderAppearance() {
      var variant = window.PGTheme.getVariant();
      var mode = window.PGTheme.getMode();
      variantButtons.forEach(function (btn) {
        btn.classList.toggle("active", btn.dataset.variant === variant);
      });
      modeButtons.forEach(function (btn) {
        btn.classList.toggle("active", btn.dataset.mode === mode);
      });
      var order = ["system", "light", "dark"];
      var idx = order.indexOf(mode);
      if (modeThumb) {
        modeThumb.style.left = "calc(3px + (100% - 6px) / 3 * " + idx + ")";
      }
    }
    renderAppearance();

    if (footerBtn) {
      footerBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        menu.classList.toggle("hidden");
      });
    }
    document.addEventListener("click", function (e) {
      if (
        !menu.classList.contains("hidden") &&
        !menu.contains(e.target) &&
        e.target !== footerBtn
      ) {
        menu.classList.add("hidden");
      }
    });
    menu.addEventListener("click", function (e) {
      e.stopPropagation();
    });

    variantButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        window.PGTheme.setVariant(btn.dataset.variant);
        renderAppearance();
      });
    });
    modeButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        window.PGTheme.setMode(btn.dataset.mode);
        renderAppearance();
      });
    });
  }

  document.addEventListener("DOMContentLoaded", setupUserMenu);
})();
