(function () {
  "use strict";

  var isLoading = false;

  // Sidebar collapse, the appearance menu, and the model-settings modal live in
  // shell.js (shared with the upload screen). chat.js only owns the right-hand
  // conversation panel and the transcript.
  var loadSettings = window.PGShell.loadSettings;
  var saveSetting = window.PGShell.saveSetting;
  var getCsrfToken = window.PGShell.getCsrfToken;

  /* ---------------- conversation settings (right panel) ---------------- */

  function setupRightPanel() {
    var panel = document.getElementById("right-panel");
    var toggle = document.getElementById("right-panel-toggle");
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

    if (toggle && panel) {
      toggle.addEventListener("click", function () {
        panel.classList.toggle("hidden");
        toggle.classList.toggle("active", !panel.classList.contains("hidden"));
      });
    }
    if (closeBtn && panel && toggle) {
      closeBtn.addEventListener("click", function () {
        panel.classList.add("hidden");
        toggle.classList.remove("active");
      });
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

  /* ---------------- chat transcript ---------------- */

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

  function setChatHeader() {
    var title = document.getElementById("chat-title");
    var subtitle = document.getElementById("chat-subtitle");
    var count = document.querySelectorAll("#chat-messages .chat-bubble.user").length;
    if (count === 0) {
      title.textContent = "Nova conversa";
      subtitle.textContent = "Banco de provas · busca semântica";
    } else {
      subtitle.textContent = count + " pergunta(s) nesta sessão";
    }
  }

  function renderMarkdownInto(el, source) {
    el.innerHTML = marked.parse(source || "");
    if (typeof renderMathInElement === "function") {
      renderMathInElement(el, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "$", right: "$", display: false },
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
    setChatHeader();
    scrollToBottom();
    return bubble;
  }

  function appendLoadingBubble() {
    var container = document.getElementById("chat-messages");
    var bubble = document.createElement("div");
    bubble.className = "chat-bubble loading";
    bubble.innerHTML =
      '<div class="assistant-avatar">PG</div>' +
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

  function buildQuestaoCard(source) {
    var questao = source.questao || {};
    var provas = source.provas || [];
    var prova = provas[0] || {};

    var card = document.createElement("div");
    card.className = "questao-card";

    var header = document.createElement("div");
    header.className = "questao-meta";

    var scoreBadge = document.createElement("span");
    scoreBadge.className = "score-badge";
    scoreBadge.textContent =
      typeof source.score === "number" ? source.score.toFixed(3) : "";
    header.appendChild(scoreBadge);

    var materiaInfo = document.createElement("span");
    materiaInfo.className = "materia-info";
    materiaInfo.textContent =
      (prova.materia || "Matéria") + " · Questão " + (questao.numero || "?");
    header.appendChild(materiaInfo);

    card.appendChild(header);

    if (prova.professor || prova.ano_semestre || prova.numero_avaliacao) {
      var profLine = document.createElement("div");
      profLine.className = "questao-prof";
      var parts = [];
      if (prova.professor) parts.push(prova.professor);
      if (prova.ano_semestre) parts.push(prova.ano_semestre);
      if (prova.numero_avaliacao) {
        parts.push("P" + prova.numero_avaliacao);
      }
      profLine.textContent = parts.join(" · ");
      card.appendChild(profLine);
    }

    var enunciado = document.createElement("div");
    enunciado.className = "md-content";
    renderMarkdownInto(enunciado, questao.enunciado);
    card.appendChild(enunciado);

    if (questao.resposta) {
      var details = document.createElement("details");
      details.className = "resposta-toggle";
      var summary = document.createElement("summary");
      summary.textContent = "Ver resolução";
      details.appendChild(summary);
      var respostaContent = document.createElement("div");
      respostaContent.className = "md-content";
      renderMarkdownInto(respostaContent, questao.resposta);
      details.appendChild(respostaContent);
      card.appendChild(details);
    }

    return card;
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

    var header = document.createElement("div");
    header.className = "assistant-header";
    header.innerHTML =
      '<div class="assistant-avatar">PG</div>' +
      '<span class="assistant-label">Exam GPT responde</span>';
    bubble.appendChild(header);

    var content = document.createElement("div");
    content.className = "md-content";
    bubble.appendChild(content);
    bubble._content = content;

    container.appendChild(bubble);
    scrollToBottom();
    return bubble;
  }

  function finishAssistantBubble(bubble, sources) {
    if (sources && sources.length) {
      var sourcesSection = document.createElement("details");
      sourcesSection.className = "sources-section";

      var summary = document.createElement("summary");
      summary.innerHTML =
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>' +
        "Fontes citadas (" + sources.length + ")";
      sourcesSection.appendChild(summary);

      sources.forEach(function (source) {
        sourcesSection.appendChild(buildQuestaoCard(source));
      });

      bubble.appendChild(sourcesSection);
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

  document.addEventListener("DOMContentLoaded", function () {
    setupAutoResize();
    setupRightPanel();
  });

  window.sendMessage = sendMessage;
  window.sendSuggestion = sendSuggestion;
  window.handleEnter = handleEnter;
})();
