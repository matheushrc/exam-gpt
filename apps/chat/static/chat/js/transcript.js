/* Chat transcript: message rendering, the streaming send/receive loop, and
   the textarea auto-resize. Depends on window.PGShell (shell-core.js). */
(function () {
  "use strict";

  var isLoading = false;

  // In-memory only: holds pydantic-ai's serialized message history for this
  // page session so follow-up questions can reference earlier turns. Lost on
  // reload by design — there's no server-side conversation storage.
  var conversationHistory = null;

  var loadSettings = window.PGShell.loadSettings;
  var getCsrfToken = window.PGShell.getCsrfToken;

  function scrollToBottom() {
    var container = document.getElementById("chat-scroll");
    container.scrollTop = container.scrollHeight;
  }

  function removeWelcome() {
    var welcome = document.getElementById("chat-welcome");
    if (welcome) {
      welcome.remove();
    }
  }

  function preprocessMarkdown(text) {
    if (!text) return "";
    return text
      .replace(/\$\$([\s\S]*?)\$\$/g, function (match, blockMath) {
        return "$$" + blockMath.replace(/\|/g, "\\vert") + "$$";
      })
      .replace(/\\\(([\s\S]*?)\\\)/g, function (match, inlineMath) {
        return "\\(" + inlineMath.replace(/\|/g, "\\vert") + "\\)";
      });
  }

  function renderMarkdownInto(el, source) {
    var cleanSource = preprocessMarkdown(source || "");
    el.innerHTML = marked.parse(cleanSource);
    if (typeof renderMathInElement === "function") {
      renderMathInElement(el, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "\\(", right: "\\)", display: false },
        ],
      });
    }
  }

  function appendUserBubble(text) {
    var container = document.getElementById("chat-messages");
    var bubble = document.createElement("div");
    bubble.className = "chat-bubble user";
    bubble.textContent = text;
    container.appendChild(bubble);
    scrollToBottom();
    return bubble;
  }

  function appendLoadingBubble() {
    var container = document.getElementById("chat-messages");
    var bubble = document.createElement("div");
    bubble.className = "chat-bubble loading";
    bubble.innerHTML =
      '<div class="assistant-avatar">EG</div>' +
      '<span class="dot-pulse"><span></span><span></span><span></span></span>';
    container.appendChild(bubble);
    scrollToBottom();
    return bubble;
  }

  function appendErrorBubble(message) {
    var container = document.getElementById("chat-messages");
    var bubble = document.createElement("div");
    bubble.className = "chat-bubble error";
    bubble.textContent = message;
    container.appendChild(bubble);
    scrollToBottom();
    return bubble;
  }

  function appendAssistantBubble(answer, sources) {
    var bubble = startAssistantBubble();
    renderMarkdownInto(bubble._content, answer);
    finishAssistantBubble(bubble, sources);
    return bubble;
  }

  function startAssistantBubble() {
    var container = document.getElementById("chat-messages");
    var bubble = document.createElement("div");
    bubble.className = "chat-bubble assistant";

    var content = document.createElement("div");
    content.className = "md-content";
    bubble.appendChild(content);
    bubble._content = content;

    container.appendChild(bubble);
    scrollToBottom();
    return bubble;
  }

  function finishAssistantBubble(bubble, sources) {
    var section = window.PGReferences.buildSourcesSection(sources, renderMarkdownInto);
    if (section) {
      bubble.appendChild(section);
    }
    scrollToBottom();
  }

  function sendText(text) {
    var t = (text || "").trim();
    if (!t || isLoading) {
      return;
    }

    removeWelcome();
    appendUserBubble(t);

    var input = document.getElementById("chat-input");
    input.value = "";
    input.style.height = "auto";

    var loadingBubble = appendLoadingBubble();
    isLoading = true;

    var settings = loadSettings();
    var headers = {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    };
    if (settings.apiKey) {
      headers["X-Google-Api-Key"] = settings.apiKey;
    }

    var payload = {
      message: t,
      grounding: settings.grounding,
      model: settings.model,
      top_k: settings.topK,
      similarity_threshold: settings.similarity,
      temperature: settings.temperature,
      max_tokens: settings.maxTokens,
      message_history: conversationHistory,
    };

    var bubble = null;
    var answerText = "";

    function ensureBubble() {
      if (!bubble) {
        loadingBubble.remove();
        bubble = startAssistantBubble();
      }
      return bubble;
    }

    fetch("/api/chat/stream/", {
      method: "POST",
      headers: headers,
      body: JSON.stringify(payload),
    })
      .then(function (response) {
        if (!response.ok) {
          return response
            .json()
            .catch(function () {
              return {};
            })
            .then(function (data) {
              throw new Error(
                data.detail || "Erro ao obter resposta do servidor."
              );
            });
        }

        var reader = response.body.getReader();
        var decoder = new TextDecoder();
        var buffer = "";

        function pump() {
          return reader.read().then(function (result) {
            if (result.done) {
              return;
            }
            buffer += decoder.decode(result.value, { stream: true });
            var frames = buffer.split("\n\n");
            buffer = frames.pop();

            frames.forEach(function (frame) {
              if (!frame.startsWith("data: ")) {
                return;
              }
              var event = JSON.parse(frame.slice(6));
              if (event.type === "delta") {
                answerText += event.text;
                renderMarkdownInto(ensureBubble()._content, answerText);
                scrollToBottom();
              } else if (event.type === "done") {
                conversationHistory = event.message_history || null;
                finishAssistantBubble(ensureBubble(), event.sources);
              } else if (event.type === "error") {
                throw new Error(event.detail);
              }
            });

            return pump();
          });
        }

        return pump();
      })
      .catch(function (err) {
        loadingBubble.remove();
        appendErrorBubble(
          err.message || "Ocorreu um erro ao enviar sua mensagem."
        );
      })
      .finally(function () {
        isLoading = false;
      });
  }

  function sendMessage() {
    var input = document.getElementById("chat-input");
    sendText(input.value);
  }

  function sendSuggestion(btn) {
    var input = document.getElementById("chat-input");
    input.value = btn.textContent.trim();
    sendMessage();
  }

  function handleEnter(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  function setupAutoResize() {
    var input = document.getElementById("chat-input");
    if (!input) {
      return;
    }
    input.addEventListener("input", function () {
      input.style.height = "auto";
      input.style.height = input.scrollHeight + "px";
    });
  }

  document.addEventListener("DOMContentLoaded", setupAutoResize);

  window.sendMessage = sendMessage;
  window.sendSuggestion = sendSuggestion;
  window.handleEnter = handleEnter;
})();
