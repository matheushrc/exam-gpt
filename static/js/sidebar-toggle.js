/* Left sidebar collapse/expand. Depends on window.PGShell.springWidth
   (shell-core.js). */
(function () {
  "use strict";

  function setupSidebarToggle() {
    var toggle = document.getElementById("sidebar-toggle");
    var mobileToggle = document.getElementById("sidebar-mobile-toggle");
    var mobileClose = document.getElementById("sidebar-mobile-close");
    var collapsedLogo = document.getElementById("sidebar-collapsed-logo");
    var sidebar = document.getElementById("sidebar");
    if (!sidebar) {
      return;
    }
    function setMobileDrawer(open) {
      sidebar.classList.toggle("mobile-open", open);
      sidebar.setAttribute("aria-hidden", String(!open));
      if (mobileToggle) {
        mobileToggle.setAttribute("aria-expanded", String(open));
      }
      if (mobileClose) {
        mobileClose.setAttribute("aria-expanded", String(open));
      }
    }
    function setDesktopSidebar() {
      sidebar.classList.remove("mobile-open");
      sidebar.setAttribute("aria-hidden", "false");
      if (mobileToggle) {
        mobileToggle.setAttribute("aria-expanded", "false");
      }
      if (mobileClose) {
        mobileClose.setAttribute("aria-expanded", "false");
      }
    }
    function toggleCollapse() {
      if (window.PGShell.isCompactViewport()) {
        return;
      }
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
    if (mobileToggle) {
      mobileToggle.addEventListener("click", function () {
        setMobileDrawer(true);
      });
    }
    if (mobileClose) {
      mobileClose.addEventListener("click", function () {
        setMobileDrawer(false);
      });
    }
    window.PGShell.onViewportChange(function (isCompact) {
      sidebar.classList.toggle("is-compact", isCompact);
      if (isCompact) {
        setMobileDrawer(false);
      } else {
        setDesktopSidebar();
      }
    });
  }

  document.addEventListener("DOMContentLoaded", setupSidebarToggle);
})();
