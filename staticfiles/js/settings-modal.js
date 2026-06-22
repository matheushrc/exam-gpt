/* Model-settings modal (API key + model picker). Depends on
   window.PGShell.loadSettings/saveSetting (shell-core.js). */
(function () {
  "use strict";

  function setupSettingsModal() {
    var modal = document.getElementById("settings-modal");
    if (!modal) {
      return;
    }
    var loadSettings = window.PGShell.loadSettings;
    var saveSetting = window.PGShell.saveSetting;

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

  document.addEventListener("DOMContentLoaded", setupSettingsModal);
})();
