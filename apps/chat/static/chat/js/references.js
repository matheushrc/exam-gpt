/* RAG reference card rendering. Clones <template> elements defined in
   _reference_templates.html and populates them with source data.
   Depends on: the two <template> elements being in the DOM.
   Exposes: window.PGReferences */
(function () {
  "use strict";

  function cloneTemplate(id) {
    var tpl = document.getElementById(id);
    if (!tpl) {
      throw new Error("Missing template: #" + id);
    }
    return tpl.content.cloneNode(true).firstElementChild;
  }

  function buildQuestaoCard(source, renderMarkdownInto) {
    var questao = source.questao || {};
    var provas = source.provas || [];
    var prova = provas[0] || {};
    var score = typeof source.score === "number" ? source.score : null;

    var card = cloneTemplate("pg-questao-card-tpl");

    // Score badge value
    if (score !== null) {
      card.querySelector(".score-value").textContent = score.toFixed(3);
    }

    // Accent bar and badge similarity classes (calculated and provided by server)
    var tier = source.similarity_tier || "low";
    card.querySelector(".card-accent-bar").classList.add(tier);
    card.querySelector(".score-badge").classList.add(tier);

    // Matéria chip
    card.querySelector(".materia-chip").textContent = prova.materia || "Matéria";

    // Questão number
    card.querySelector(".ordem-chip").textContent =
      "Questão " + (questao.ordem || "?");

    // Prof / semester row — build with <span> and separator dots
    var row2 = card.querySelector(".questao-meta-row2");
    var parts = [];
    if (prova.professor) parts.push(prova.professor);
    if (prova.ano_semestre) parts.push(prova.ano_semestre);
    if (prova.numero_avaliacao) parts.push("P" + prova.numero_avaliacao);
    parts.forEach(function (text, i) {
      var span = document.createElement("span");
      span.textContent = text;
      row2.appendChild(span);
      if (i < parts.length - 1) {
        var sep = document.createElement("span");
        sep.className = "meta-sep";
        sep.textContent = "·";
        row2.appendChild(sep);
      }
    });

    // Enunciado
    renderMarkdownInto(card.querySelector(".enunciado-content"), questao.enunciado);

    // Resolução
    if (questao.resposta) {
      card.classList.add("has-resposta");
      renderMarkdownInto(card.querySelector(".resposta-content"), questao.resposta);
    }

    return card;
  }

  function buildSourcesSection(sources, renderMarkdownInto) {
    if (!sources || !sources.length) {
      return null;
    }

    var section = cloneTemplate("pg-sources-section-tpl");
    section.querySelector(".sources-count").textContent = sources.length;

    var list = section.querySelector(".sources-list");
    sources.forEach(function (source) {
      list.appendChild(buildQuestaoCard(source, renderMarkdownInto));
    });

    return section;
  }

  window.PGReferences = {
    buildSourcesSection: buildSourcesSection,
  };
})();
