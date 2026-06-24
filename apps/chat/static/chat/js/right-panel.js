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

    var desktopWasCollapsed = panel.classList.contains("collapsed");

    // On mobile the panel is a full-screen overlay controlled by CSS width. On
    // desktop it is an inline column whose width animates with the spring; pin
    // the current width inline before flipping the class for user-triggered
    // changes so the spring starts from the visible width.
    function collapsePanel(skipSpring) {
      toggle.classList.remove("active");
      if (window.PGShell.isCompactViewport()) {
        panel.classList.remove("mobile-open");
        panel.classList.add("collapsed");
        return;
      }
      if (skipSpring) {
        panel.style.width = "";
        panel.classList.add("collapsed");
        return;
      }
      panel.style.width = panel.getBoundingClientRect().width + "px";
      panel.classList.add("collapsed");
      springWidth(panel, 0);
    }
    function expandPanel(skipSpring) {
      toggle.classList.add("active");
      if (window.PGShell.isCompactViewport()) {
        panel.classList.add("mobile-open");
        panel.classList.remove("collapsed");
        return;
      }
      if (skipSpring) {
        panel.style.width = "";
        panel.classList.remove("collapsed");
        return;
      }
      panel.style.width = panel.getBoundingClientRect().width + "px";
      panel.classList.remove("collapsed");
      var target = getComputedStyle(panel).getPropertyValue("--right-panel-width");
      springWidth(panel, parseFloat(target));
    }
    window.PGShell.onViewportChange(function (isCompact) {
      panel.classList.add("viewport-switching");
      requestAnimationFrame(function () {
        panel.classList.remove("viewport-switching");
      });
      panel.classList.toggle("is-compact", isCompact);
      if (isCompact) {
        desktopWasCollapsed = panel.classList.contains("collapsed");
        panel.classList.remove("mobile-open");
        collapsePanel(true);
      } else {
        panel.classList.remove("mobile-open");
        if (desktopWasCollapsed) {
          collapsePanel(true);
        } else {
          expandPanel(true);
        }
      }
    });
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
