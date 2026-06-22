/* Right-hand conversation-settings panel: grounding toggle, retriever
   sliders, and the collapse/expand spring. Depends on window.PGShell
   (shell-core.js, shared with the upload screen). */
(function () {
  "use strict";

  function setupRightPanel() {
    var panel = document.getElementById("right-panel");
    var toggle = document.getElementById("right-panel-toggle");
    if (!panel || !toggle) {
      return;
    }
    var loadSettings = window.PGShell.loadSettings;
    var saveSetting = window.PGShell.saveSetting;
    var springWidth = window.PGShell.springWidth;

    var closeBtn = document.getElementById("right-panel-close");
    var groundingBtn = document.getElementById("setting-grounding");
    var groundStatusText = document.getElementById("ground-status-text");
    var ragGroup = document.getElementById("rag-group");
    var topKInput = document.getElementById("setting-top-k");
    var topKValue = document.getElementById("top-k-value");
    var similarityInput = document.getElementById("setting-similarity");
    var similarityValue = document.getElementById("similarity-value");
    var temperatureInput = document.getElementById("setting-temperature");
    var temperatureValue = document.getElementById("temperature-value");
    var maxTokensInput = document.getElementById("setting-max-tokens");

    var settings = loadSettings();

    function renderGrounding() {
      groundingBtn.classList.toggle("checked", settings.grounding);
      groundingBtn.setAttribute("aria-checked", String(settings.grounding));
      groundStatusText.textContent = settings.grounding
        ? "A IA decide quando recuperar"
        : "Sem recuperação — só o modelo";
      ragGroup.classList.toggle("disabled", !settings.grounding);
    }

    topKInput.value = settings.topK;
    topKValue.textContent = settings.topK;
    similarityInput.value = settings.similarity;
    similarityValue.textContent = settings.similarity.toFixed(2);
    temperatureInput.value = settings.temperature;
    temperatureValue.textContent = settings.temperature.toFixed(1);
    maxTokensInput.value = settings.maxTokens;
    renderGrounding();

    // Pin the current width inline before flipping the class -- otherwise
    // the CSS width rule snaps instantly and the spring starts from the
    // target width instead of animating to it.
    function collapsePanel() {
      panel.style.width = panel.getBoundingClientRect().width + "px";
      panel.classList.add("collapsed");
      toggle.classList.remove("active");
      springWidth(panel, 0);
    }
    function expandPanel() {
      panel.style.width = panel.getBoundingClientRect().width + "px";
      panel.classList.remove("collapsed");
      toggle.classList.add("active");
      var target = getComputedStyle(panel).getPropertyValue("--right-panel-width");
      springWidth(panel, parseFloat(target));
    }
    toggle.addEventListener("click", function () {
      if (panel.classList.contains("collapsed")) {
        expandPanel();
      } else {
        collapsePanel();
      }
    });
    if (closeBtn) {
      closeBtn.addEventListener("click", collapsePanel);
    }

    groundingBtn.addEventListener("click", function () {
      settings.grounding = !settings.grounding;
      saveSetting("grounding", settings.grounding);
      renderGrounding();
    });
    topKInput.addEventListener("input", function () {
      settings.topK = Number(topKInput.value);
      topKValue.textContent = settings.topK;
      saveSetting("topK", settings.topK);
    });
    similarityInput.addEventListener("input", function () {
      settings.similarity = Number(similarityInput.value);
      similarityValue.textContent = settings.similarity.toFixed(2);
      saveSetting("similarity", settings.similarity);
    });
    temperatureInput.addEventListener("input", function () {
      settings.temperature = Number(temperatureInput.value);
      temperatureValue.textContent = settings.temperature.toFixed(1);
      saveSetting("temperature", settings.temperature);
    });
    maxTokensInput.addEventListener("input", function () {
      settings.maxTokens = Number(maxTokensInput.value) || 8192;
      saveSetting("maxTokens", settings.maxTokens);
    });
  }

  document.addEventListener("DOMContentLoaded", setupRightPanel);
})();
