/* App shell shared across pages (chat + upload): sidebar collapse, the
   appearance/user menu, the model-settings modal, and the localStorage-backed
   settings store. Page-specific scripts (chat.js, upload-screen.js) build on
   top of window.PGShell instead of re-implementing this. */
(function () {
  "use strict";

  var STORAGE_KEYS = {
    model: "pg.chatModel",
    apiKey: "pg.apiKey",
    grounding: "pg.grounding",
    topK: "pg.topK",
    similarity: "pg.similarity",
    temperature: "pg.temperature",
    maxTokens: "pg.maxTokens",
  };

  function getCsrfToken() {
    var match = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function loadSettings() {
    return {
      model: localStorage.getItem(STORAGE_KEYS.model) || "gemini-3.1-flash-lite",
      apiKey: localStorage.getItem(STORAGE_KEYS.apiKey) || "",
      grounding: localStorage.getItem(STORAGE_KEYS.grounding) !== "false",
      topK: Number(localStorage.getItem(STORAGE_KEYS.topK) || 5),
      similarity: Number(localStorage.getItem(STORAGE_KEYS.similarity) || 0.6),
      temperature: Number(localStorage.getItem(STORAGE_KEYS.temperature) || 0),
      maxTokens: Number(localStorage.getItem(STORAGE_KEYS.maxTokens) || 8192),
    };
  }

  function saveSetting(key, value) {
    if (STORAGE_KEYS[key]) {
      localStorage.setItem(STORAGE_KEYS[key], value);
    }
  }

  function setupSidebarToggle() {
    var toggle = document.getElementById("sidebar-toggle");
    var collapsedLogo = document.getElementById("sidebar-collapsed-logo");
    var sidebar = document.getElementById("sidebar");
    if (!sidebar) {
      return;
    }
    function toggleCollapse() {
      sidebar.classList.toggle("collapsed");
    }
    if (toggle) toggle.addEventListener("click", toggleCollapse);
    if (collapsedLogo) collapsedLogo.addEventListener("click", toggleCollapse);
  }

  function setupSettingsModal() {
    var modal = document.getElementById("settings-modal");
    if (!modal) {
      return;
    }
    var openBtn = document.getElementById("open-settings-modal");
    var closeBtn = document.getElementById("settings-modal-close");
    var doneBtn = document.getElementById("settings-modal-done");
    var modelInput = document.getElementById("setting-model");
    var apiKeyInput = document.getElementById("setting-api-key");
    var presetButtons = document.querySelectorAll(".preset-chip");

    var settings = loadSettings();
    modelInput.value = settings.model;
    apiKeyInput.value = settings.apiKey;

    function renderPresets() {
      presetButtons.forEach(function (btn) {
        btn.classList.toggle("active", btn.dataset.model === modelInput.value);
      });
    }
    renderPresets();

    function open() {
      modal.classList.remove("hidden");
      var menu = document.getElementById("user-menu");
      if (menu) menu.classList.add("hidden");
    }
    function close() {
      modal.classList.add("hidden");
    }

    if (openBtn) openBtn.addEventListener("click", open);
    if (closeBtn) closeBtn.addEventListener("click", close);
    if (doneBtn) doneBtn.addEventListener("click", close);
    modal.addEventListener("click", function (e) {
      if (e.target === modal) close();
    });

    modelInput.addEventListener("input", function () {
      saveSetting("model", modelInput.value);
      renderPresets();
    });
    apiKeyInput.addEventListener("input", function () {
      saveSetting("apiKey", apiKeyInput.value);
    });
    presetButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        modelInput.value = btn.dataset.model;
        saveSetting("model", modelInput.value);
        renderPresets();
      });
    });
  }

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

  document.addEventListener("DOMContentLoaded", function () {
    setupSidebarToggle();
    setupSettingsModal();
    setupUserMenu();
  });

  window.PGShell = {
    STORAGE_KEYS: STORAGE_KEYS,
    getCsrfToken: getCsrfToken,
    loadSettings: loadSettings,
    saveSetting: saveSetting,
  };
})();
