/* Left sidebar collapse/expand. Depends on window.PGShell.springWidth
   (shell-core.js). */
(function () {
  "use strict";

  function setupSidebarToggle() {
    var toggle = document.getElementById("sidebar-toggle");
    var collapsedLogo = document.getElementById("sidebar-collapsed-logo");
    var sidebar = document.getElementById("sidebar");
    if (!sidebar) {
      return;
    }
    function toggleCollapse() {
      var collapsing = !sidebar.classList.contains("collapsed");
      // Pin the current width inline first -- otherwise toggling the class
      // snaps the CSS width rule instantly, and the spring would start from
      // the already-collapsed/expanded width instead of animating to it.
      sidebar.style.width = sidebar.getBoundingClientRect().width + "px";
      sidebar.classList.toggle("collapsed");
      var target = getComputedStyle(sidebar).getPropertyValue(
        collapsing ? "--sidebar-collapsed-width" : "--sidebar-width",
      );
      window.PGShell.springWidth(sidebar, parseFloat(target));
    }
    if (toggle) toggle.addEventListener("click", toggleCollapse);
    if (collapsedLogo) collapsedLogo.addEventListener("click", toggleCollapse);
  }

  document.addEventListener("DOMContentLoaded", setupSidebarToggle);
})();
