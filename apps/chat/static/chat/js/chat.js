(function () {
  "use strict";

  var isLoading = false;

  function getCsrfToken() {
    var match = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function scrollToBottom() {
    var container = document.getElementById("chat-messages");
    container.scrollTop = container.scrollHeight;
  }

  function removeWelcome() {
    var welcome = document.getElementById("chat-welcome");
    if (welcome) {
      welcome.remove();
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
    scrollToBottom();
    return bubble;
  }

  function appendLoadingBubble() {
    var container = document.getElementById("chat-messages");
    var bubble = document.createElement("div");
    bubble.className = "chat-bubble assistant loading";
    bubble.innerHTML =
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
    materiaInfo.textContent =
      (prova.materia || "Matéria") + " · Q" + (questao.numero || "?");
    header.appendChild(materiaInfo);

    card.appendChild(header);

    if (prova.professor || prova.ano_semestre || prova.numero_avaliacao) {
      var profLine = document.createElement("div");
      profLine.className = "questao-prof";
      var parts = [];
      if (prova.professor) parts.push(prova.professor);
      if (prova.ano_semestre) parts.push(prova.ano_semestre);
      if (prova.numero_avaliacao) {
        parts.push("Avaliação " + prova.numero_avaliacao);
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
      summary.textContent = "Ver resposta";
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
    var container = document.getElementById("chat-messages");
    var bubble = document.createElement("div");
    bubble.className = "chat-bubble assistant";

    var content = document.createElement("div");
    content.className = "md-content";
    renderMarkdownInto(content, answer);
    bubble.appendChild(content);

    if (sources && sources.length) {
      var sourcesSection = document.createElement("details");
      sourcesSection.className = "sources-section";

      var summary = document.createElement("summary");
      summary.textContent = "Fontes (" + sources.length + ")";
      sourcesSection.appendChild(summary);

      sources.forEach(function (source) {
        sourcesSection.appendChild(buildQuestaoCard(source));
      });

      bubble.appendChild(sourcesSection);
    }

    container.appendChild(bubble);
    scrollToBottom();
    return bubble;
  }

  function sendMessage() {
    if (isLoading) {
      return;
    }

    var input = document.getElementById("chat-input");
    var text = input.value.trim();
    if (!text) {
      return;
    }

    removeWelcome();
    appendUserBubble(text);

    input.value = "";
    input.style.height = "auto";

    var loadingBubble = appendLoadingBubble();
    isLoading = true;

    fetch("/api/chat/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({ message: text }),
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
        return response.json();
      })
      .then(function (data) {
        loadingBubble.remove();
        appendAssistantBubble(data.answer, data.sources);
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

  function setupSidebarToggle() {
    var toggle = document.getElementById("sidebar-toggle");
    var sidebar = document.getElementById("sidebar");
    if (toggle && sidebar) {
      toggle.addEventListener("click", function () {
        sidebar.classList.toggle("collapsed");
      });
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
    setupSidebarToggle();
    setupAutoResize();
  });

  window.sendMessage = sendMessage;
  window.sendSuggestion = sendSuggestion;
  window.handleEnter = handleEnter;
  window.getCsrfToken = getCsrfToken;
})();
