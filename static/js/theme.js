(function () {
  "use strict";

  var VARIANT_KEY = "pg.themeVariant";
  var MODE_KEY = "pg.themeMode";
  var VARIANTS = ["manuscrito", "periodico", "academico"];

  function getVariant() {
    var v = localStorage.getItem(VARIANT_KEY);
    return VARIANTS.indexOf(v) !== -1 ? v : "manuscrito";
  }

  function getMode() {
    var m = localStorage.getItem(MODE_KEY);
    return m === "light" || m === "dark" || m === "system" ? m : "system";
  }

  function resolveTheme(mode) {
    if (mode === "system") {
      return window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
    }
    return mode;
  }

  function apply() {
    var variant = getVariant();
    var mode = getMode();
    var root = document.documentElement;
    root.setAttribute("data-variant", variant);
    root.setAttribute("data-theme", resolveTheme(mode));
  }

  function setVariant(variant) {
    localStorage.setItem(VARIANT_KEY, variant);
    apply();
  }

  function setMode(mode) {
    localStorage.setItem(MODE_KEY, mode);
    apply();
  }

  apply();

  window
    .matchMedia("(prefers-color-scheme: dark)")
    .addEventListener("change", function () {
      if (getMode() === "system") {
        apply();
      }
    });

  window.PGTheme = {
    VARIANTS: VARIANTS,
    getVariant: getVariant,
    getMode: getMode,
    setVariant: setVariant,
    setMode: setMode,
  };
})();
