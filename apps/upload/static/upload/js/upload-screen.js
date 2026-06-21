/* DC "Enviar prova" screen: empty -> processing -> review, driven against the
   JSON endpoints /api/provas/extract/ and /api/provas/. The model/API-key
   settings come from the shared shell (window.PGShell). */
(function () {
  "use strict";

  var META_FIELDS = [
    { key: "materia", label: "Matéria", type: "text" },
    { key: "professor", label: "Professor", type: "text" },
    { key: "ano_semestre", label: "Ano / Semestre", type: "text" },
    { key: "data_aplicacao", label: "Data de aplicação", type: "date" },
    { key: "numero_avaliacao", label: "Nº da avaliação", type: "number" },
    { key: "cursos", label: "Curso(s)", type: "text", list: true },
  ];

  var prova = null;
  var fileNames = [];
  var saving = false;

  var els = {};

  function $(id) {
    return document.getElementById(id);
  }

  function showStage(stage) {
    els.empty.classList.toggle("hidden", stage !== "empty");
    els.processing.classList.toggle("hidden", stage !== "processing");
    els.review.classList.toggle("hidden", stage !== "review");
    els.footer.classList.toggle("hidden", stage !== "review");
  }

  function renderMarkdownInto(el, source) {
    if (typeof marked !== "undefined") {
      el.innerHTML = marked.parse(source || "");
    } else {
      el.textContent = source || "";
    }
    if (typeof renderMathInElement === "function") {
      renderMathInElement(el, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "$", right: "$", display: false },
        ],
      });
    }
  }

  /* ---------------- extraction ---------------- */

  function startExtraction(files) {
    if (!files || !files.length) {
      return;
    }
    fileNames = Array.prototype.map.call(files, function (f) {
      return f.name;
    });
    els.processingTitle.textContent =
      "Extraindo questões de " + fileNames[0] + "…";
    els.error.classList.add("hidden");
    showStage("processing");

    var settings = window.PGShell.loadSettings();
    var headers = { "X-CSRFToken": window.PGShell.getCsrfToken() };
    if (settings.apiKey) {
      headers["X-Google-Api-Key"] = settings.apiKey;
    }

    var form = new FormData();
    Array.prototype.forEach.call(files, function (f) {
      form.append("files", f);
    });

    fetch("/api/provas/extract/", {
      method: "POST",
      headers: headers,
      body: form,
    })
      .then(function (response) {
        return response.json().then(function (data) {
          if (!response.ok) {
            throw new Error(data.detail || "Falha ao extrair a prova.");
          }
          return data;
        });
      })
      .then(function (data) {
        prova = data.prova;
        if (data.file_names && data.file_names.length) {
          fileNames = data.file_names;
        }
        renderReview();
        showStage("review");
      })
      .catch(function (err) {
        els.error.textContent =
          err.message || "Ocorreu um erro ao extrair a prova.";
        els.error.classList.remove("hidden");
        showStage("empty");
      });
  }

  /* ---------------- review rendering ---------------- */

  function renderReview() {
    var questoes = prova.questoes || [];

    els.filename.textContent = fileNames.join(", ") || "Arquivo enviado";
    var withAnswers = questoes.filter(function (q) {
      return q.resposta;
    }).length;
    els.filesub.textContent =
      questoes.length +
      " quest" +
      (questoes.length === 1 ? "ão" : "ões") +
      " extraída" +
      (questoes.length === 1 ? "" : "s") +
      " · " +
      withAnswers +
      " com gabarito";

    renderMeta();
    renderRecToggle();
    renderQuestions(questoes);

    els.footerText.textContent =
      questoes.length +
      " quest" +
      (questoes.length === 1 ? "ão pronta" : "ões prontas") +
      " para indexação no banco.";
  }

  function renderMeta() {
    els.meta.innerHTML = "";
    META_FIELDS.forEach(function (field) {
      var label = document.createElement("label");
      label.className = "review-meta-field";

      var span = document.createElement("span");
      span.className = "review-meta-label";
      span.textContent = field.label;
      label.appendChild(span);

      var input = document.createElement("input");
      input.type = field.type;
      var value = prova[field.key];
      if (field.list && Array.isArray(value)) {
        value = value.join(", ");
      }
      input.value = value == null ? "" : value;
      input.addEventListener("input", function () {
        var v = input.value;
        if (field.list) {
          prova[field.key] = v
            .split(",")
            .map(function (s) {
              return s.trim();
            })
            .filter(Boolean);
        } else if (field.type === "number") {
          prova[field.key] = v === "" ? null : Number(v);
        } else {
          prova[field.key] = v;
        }
      });
      label.appendChild(input);
      els.meta.appendChild(label);
    });
  }

  function renderRecToggle() {
    var on = !!prova.recuperacao;
    els.recToggle.classList.toggle("checked", on);
    els.recToggle.setAttribute("aria-checked", String(on));
  }

  function renderQuestions(questoes) {
    els.questionsCount.textContent =
      "Questões extraídas (" + questoes.length + ")";

    var total = questoes.reduce(function (sum, q) {
      return sum + (Number(q.pontuacao) || 0);
    }, 0);
    els.questionsTotal.textContent = total
      ? total.toLocaleString("pt-BR") + " pts no total"
      : "";

    els.questions.innerHTML = "";
    questoes.forEach(function (q) {
      var card = document.createElement("div");
      card.className = "review-question-card";

      var head = document.createElement("div");
      head.className = "review-question-head";

      var num = document.createElement("span");
      num.className = "review-question-num";
      num.textContent = "Q" + (q.numero != null ? q.numero : "?");
      head.appendChild(num);

      if (q.pontuacao != null) {
        var pts = document.createElement("span");
        pts.className = "review-question-pts";
        pts.textContent = Number(q.pontuacao).toLocaleString("pt-BR") + " pts";
        head.appendChild(pts);
      }

      var tag = document.createElement("span");
      tag.className = "review-question-tag";
      tag.innerHTML =
        '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>' +
        (q.resposta ? "com gabarito" : "extraído");
      head.appendChild(tag);
      card.appendChild(head);

      var enun = document.createElement("div");
      enun.className = "review-question-enunciado md-content";
      renderMarkdownInto(enun, q.enunciado);
      card.appendChild(enun);

      if (q.resposta) {
        var details = document.createElement("details");
        details.className = "review-question-answer";
        var summary = document.createElement("summary");
        summary.textContent = "Ver resolução";
        details.appendChild(summary);
        var ans = document.createElement("div");
        ans.className = "md-content";
        renderMarkdownInto(ans, q.resposta);
        details.appendChild(ans);
        card.appendChild(details);
      }

      els.questions.appendChild(card);
    });
  }

  /* ---------------- save ---------------- */

  function save() {
    if (saving || !prova) {
      return;
    }
    saving = true;
    els.save.disabled = true;
    els.error.classList.add("hidden");

    fetch("/api/provas/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": window.PGShell.getCsrfToken(),
      },
      body: JSON.stringify({ prova: prova }),
    })
      .then(function (response) {
        return response.json().then(function (data) {
          if (!response.ok) {
            throw new Error(data.detail || "Falha ao salvar a prova.");
          }
          return data;
        });
      })
      .then(function () {
        window.location.href = "/";
      })
      .catch(function (err) {
        els.error.textContent =
          err.message || "Ocorreu um erro ao salvar a prova.";
        els.error.classList.remove("hidden");
        showStage("empty");
      })
      .finally(function () {
        saving = false;
        els.save.disabled = false;
      });
  }

  function reset() {
    prova = null;
    fileNames = [];
    els.fileInput.value = "";
    showStage("empty");
  }

  /* ---------------- wiring ---------------- */

  document.addEventListener("DOMContentLoaded", function () {
    els = {
      empty: $("upload-empty"),
      processing: $("upload-processing"),
      review: $("upload-review"),
      footer: $("review-footer"),
      footerText: $("review-footer-text"),
      dropzone: $("upload-dropzone"),
      fileInput: $("upload-file-input"),
      processingTitle: $("processing-title"),
      error: $("upload-error"),
      filename: $("review-filename"),
      filesub: $("review-filesub"),
      meta: $("review-meta"),
      recToggle: $("review-rec-toggle"),
      questionsCount: $("review-questions-count"),
      questionsTotal: $("review-questions-total"),
      questions: $("review-questions"),
      save: $("review-save"),
      cancel: $("review-cancel"),
      change: $("review-change"),
    };

    els.dropzone.addEventListener("click", function () {
      els.fileInput.click();
    });
    els.fileInput.addEventListener("change", function () {
      if (els.fileInput.files.length) {
        startExtraction(els.fileInput.files);
      }
    });

    ["dragenter", "dragover"].forEach(function (evt) {
      els.dropzone.addEventListener(evt, function (e) {
        e.preventDefault();
        els.dropzone.classList.add("dragging");
      });
    });
    ["dragleave", "drop"].forEach(function (evt) {
      els.dropzone.addEventListener(evt, function (e) {
        e.preventDefault();
        els.dropzone.classList.remove("dragging");
      });
    });
    els.dropzone.addEventListener("drop", function (e) {
      if (e.dataTransfer && e.dataTransfer.files.length) {
        startExtraction(e.dataTransfer.files);
      }
    });

    els.recToggle.addEventListener("click", function () {
      if (!prova) return;
      prova.recuperacao = !prova.recuperacao;
      renderRecToggle();
    });

    els.save.addEventListener("click", save);
    els.cancel.addEventListener("click", reset);
    els.change.addEventListener("click", reset);
  });
})();
