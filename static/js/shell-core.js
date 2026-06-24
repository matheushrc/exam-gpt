/* Shared utilities used by the other shell-* scripts and by chat.js: the
   localStorage-backed settings store, CSRF helper, and the spring width
   animator. Must load (and execute) before any script that reads
   window.PGShell. */
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

  // Damped-spring width animator, modeled after the slight overshoot/undershoot
  // ChatGPT's sidebar uses for its collapse/expand (a CSS ease-out reads flat
  // and mechanical by comparison). Toggling the "collapsed" class still fires
  // immediately so opacity-based content fades stay decoupled and fast; this
  // only drives the width itself.
  function springWidth(el, toPx, opts) {
    opts = opts || {};
    var stiffness = opts.stiffness || 500;
    var damping = opts.damping || 35;
    var precision = opts.precision || 0.4;
    var maxDuration = opts.maxDuration || 900;
    if (el._springRaf) cancelAnimationFrame(el._springRaf);

    var current = el.getBoundingClientRect().width;
    var velocity = 0;
    var start = performance.now();
    var last = performance.now();

    function step(now) {
      var dt = Math.min((now - last) / 1000, 0.032);
      last = now;
      var displacement = current - toPx;
      var acceleration = -stiffness * displacement - damping * velocity;
      velocity += acceleration * dt;
      current += velocity * dt;

      if (
        now - start >= maxDuration ||
        (Math.abs(displacement) < precision && Math.abs(velocity) < precision)
      ) {
        el.style.width = "";
        el._springRaf = null;
        return;
      }
      el.style.width = Math.max(current, 0) + "px";
      el._springRaf = requestAnimationFrame(step);
    }
    el._springRaf = requestAnimationFrame(step);
  }

  function isCompactViewport() {
    return window.matchMedia("(max-width: 640px)").matches;
  }

  function onViewportChange(handler) {
    var mediaQuery = window.matchMedia("(max-width: 640px)");
    function handleChange(event) {
      handler(event.matches);
    }
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener("change", handleChange);
    } else {
      mediaQuery.addListener(handleChange);
    }
    handler(mediaQuery.matches);
    return function unsubscribe() {
      if (mediaQuery.removeEventListener) {
        mediaQuery.removeEventListener("change", handleChange);
      } else {
        mediaQuery.removeListener(handleChange);
      }
    };
  }

  window.PGShell = {
    STORAGE_KEYS: STORAGE_KEYS,
    getCsrfToken: getCsrfToken,
    loadSettings: loadSettings,
    saveSetting: saveSetting,
    isCompactViewport: isCompactViewport,
    onViewportChange: onViewportChange,
    springWidth: springWidth,
  };
})();
