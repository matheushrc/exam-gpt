/* DC "Enviar prova" screen: empty -> processing -> review, driven against the
   JSON endpoints /api/provas/extract/ and /api/provas/. The model/API-key
   settings come from the shared shell (window.PGShell).

   The review stage is a full editor: the user corrects what the AI misread
   before indexing — metadata (with chip multiselects for professores e cursos),
   per-question grades, enunciados/respostas with live Markdown+LaTeX, nested
   subquestões whose points roll up into the parent, and manual question entry. */
(function () {
  "use strict";

  // Cursos da UFFS (campus). Fixed list — the prova is tagged with one or more.
  var COURSES = [
    "Administração",
    "Agronomia",
    "Ciência da Computação",
    "Ciências Econômicas",
    "Ciências Sociais",
    "Educação Especial Inclusiva - Segunda Licenciatura",
    "Enfermagem",
    "Engenharia Ambiental e Sanitária",
    "Engenharia Civil",
    "Filosofia",
    "Geografia",
    "História",
    "Letras (Português e Espanhol)",
    "Matemática",
    "Medicina",
    "Pedagogia",
  ];

  var UFFS_DOMAIN = "@uffs.edu.br";

  var prova = null;
  var fileNames = [];
  var teachers = []; // [{ email, name, username }] from /api/professors/
  var profHint = ""; // raw professor name the AI extracted, shown as a hint
  var saving = false;

  var els = {};

  function $(id) {
    return document.getElementById(id);
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function showStage(stage) {
    els.empty.classList.toggle("hidden", stage !== "empty");
    els.processing.classList.toggle("hidden", stage !== "processing");
    els.review.classList.toggle("hidden", stage !== "review");
    els.footer.classList.toggle("hidden", stage !== "review");
  }

  function renderMarkdownInto(node, source) {
    if (typeof marked !== "undefined") {
      node.innerHTML = marked.parse(source || "");
    } else {
      node.textContent = source || "";
    }
    if (typeof renderMathInElement === "function") {
      renderMathInElement(node, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "$", right: "$", display: false },
        ],
        throwOnError: false,
      });
    }
  }

  function plural(n, one, many) {
    return n === 1 ? one : many;
  }

  function fmtPts(n) {
    return Number(n || 0).toLocaleString("pt-BR", { maximumFractionDigits: 2 });
  }

  /* ---------------- extraction ---------------- */

  function startExtraction(files) {
    if (!files || !files.length) return;

    fileNames = Array.prototype.map.call(files, function (f) {
      return f.name;
    });
    els.processingTitle.textContent =
      "Extraindo questões de " + fileNames[0] + "…";
    els.error.classList.add("hidden");
    showStage("processing");

    var settings = window.PGShell.loadSettings();
    var headers = { "X-CSRFToken": window.PGShell.getCsrfToken() };
    if (settings.apiKey) headers["X-Google-Api-Key"] = settings.apiKey;

    var form = new FormData();
    Array.prototype.forEach.call(files, function (f) {
      form.append("files", f);
    });

    fetch("/api/provas/extract/", { method: "POST", headers: headers, body: form })
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
        enterReview();
      })
      .catch(function (err) {
        els.error.textContent =
          err.message || "Ocorreu um erro ao extrair a prova.";
        els.error.classList.remove("hidden");
        showStage("empty");
      });
  }

  /* ---------------- normalization ---------------- */

  // Coerce the extracted payload into the editable shape the review UI expects.
  function normalizeProva() {
    if (!Array.isArray(prova.cursos)) prova.cursos = [];

    // professor: AI extracts a name string; the field is a list of @uffs emails.
    profHint = "";
    if (typeof prova.professor === "string") {
      profHint = prova.professor.trim();
      prova.professor = [];
    } else if (!Array.isArray(prova.professor)) {
      prova.professor = [];
    }

    (prova.questoes || []).forEach(function (q) {
      if (!Array.isArray(q.subquestoes)) q.subquestoes = [];
    });
  }

  function enterReview() {
    normalizeProva();
    renderReview();
    showStage("review");
    loadTeachers();
  }

  // Fetch the CS faculty for the prova's semester. Emails are derived from the
  // UFFS username (username@uffs.edu.br); the cache only stores usernames.
  function loadTeachers() {
    var semester = prova.ano_semestre || "";
    var url = "/api/professors/";
    if (semester) url += "?semester=" + encodeURIComponent(semester);

    fetch(url)
      .then(function (r) {
        return r.ok ? r.json() : [];
      })
      .then(function (list) {
        teachers = (list || [])
          .filter(function (p) {
            return p && p.username;
          })
          .map(function (p) {
            return {
              username: p.username,
              name: p.name || p.username,
              email: p.username + UFFS_DOMAIN,
            };
          });
        prematchProfessor();
        renderProfessorField();
      })
      .catch(function () {
        teachers = [];
        renderProfessorField();
      });
  }

  // If the AI's professor name matches a known teacher, preselect their email.
  function prematchProfessor() {
    if (!profHint || prova.professor.length) return;
    var hint = profHint.toLowerCase();
    var match = teachers.find(function (t) {
      var name = t.name.toLowerCase();
      return name === hint || name.indexOf(hint) !== -1 || hint.indexOf(name) !== -1;
    });
    if (match && prova.professor.indexOf(match.email) === -1) {
      prova.professor.push(match.email);
      profHint = "";
    }
  }

  /* ---------------- chip multiselect ---------------- */

  // options: [{ value, label, sub }]. selected: array of values (mutated via cbs).
  function chipMultiSelect(opts) {
    var selected = opts.selected;
    var wrap = el("div", "ms");
    var control = el("div", "ms-control");
    var menu = el("div", "ms-menu hidden");
    var input = el("input", "ms-input");
    input.type = "text";
    input.placeholder = opts.placeholder || "";

    function optionFor(value) {
      return (opts.options || []).find(function (o) {
        return o.value === value;
      });
    }

    function add(value) {
      if (selected.indexOf(value) === -1) {
        selected.push(value);
        opts.onChange && opts.onChange();
      }
      input.value = "";
      renderChips();
      renderMenu();
      input.focus();
    }

    function remove(value) {
      var i = selected.indexOf(value);
      if (i !== -1) {
        selected.splice(i, 1);
        opts.onChange && opts.onChange();
      }
      renderChips();
      renderMenu();
    }

    function renderChips() {
      Array.prototype.slice
        .call(control.querySelectorAll(".ms-chip"))
        .forEach(function (c) {
          c.remove();
        });
      selected.forEach(function (value) {
        var found = optionFor(value);
        var chip = el("span", "ms-chip");
        chip.appendChild(el("span", "ms-chip-label", found ? found.label : value));
        if (found && found.sub && found.sub !== found.label) {
          chip.title = found.sub;
        }
        var x = el("button", "ms-chip-x");
        x.type = "button";
        x.setAttribute("aria-label", "Remover");
        x.textContent = "×";
        x.addEventListener("click", function () {
          remove(value);
        });
        chip.appendChild(x);
        control.insertBefore(chip, input);
      });
    }

    function renderMenu() {
      menu.innerHTML = "";
      var q = input.value.trim().toLowerCase();
      var available = (opts.options || []).filter(function (o) {
        if (selected.indexOf(o.value) !== -1) return false;
        if (!q) return true;
        return (
          o.label.toLowerCase().indexOf(q) !== -1 ||
          (o.sub || "").toLowerCase().indexOf(q) !== -1
        );
      });

      available.slice(0, 50).forEach(function (o) {
        var item = el("button", "ms-item");
        item.type = "button";
        item.appendChild(el("span", "ms-item-label", o.label));
        if (o.sub && o.sub !== o.label) {
          item.appendChild(el("span", "ms-item-sub", o.sub));
        }
        item.addEventListener("mousedown", function (e) {
          e.preventDefault();
          add(o.value);
        });
        menu.appendChild(item);
      });

      // Custom value (e.g. a professor not in the CS cache).
      if (opts.allowCustom && q) {
        var raw = input.value.trim();
        var valid = !opts.validateCustom || opts.validateCustom(raw);
        var custom = el("button", "ms-item ms-item-custom");
        custom.type = "button";
        if (valid) {
          custom.appendChild(el("span", "ms-item-label", "Adicionar “" + raw + "”"));
          custom.addEventListener("mousedown", function (e) {
            e.preventDefault();
            add(raw);
          });
        } else {
          custom.classList.add("ms-item-invalid");
          custom.disabled = true;
          custom.appendChild(
            el("span", "ms-item-label", opts.customHint || "Valor inválido")
          );
        }
        menu.appendChild(custom);
      }

      if (!menu.children.length) {
        menu.appendChild(el("div", "ms-empty", opts.emptyHint || "Nenhuma opção"));
      }
    }

    function openMenu() {
      renderMenu();
      menu.classList.remove("hidden");
    }
    function closeMenu() {
      menu.classList.add("hidden");
    }

    input.addEventListener("focus", openMenu);
    input.addEventListener("input", renderMenu);
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && opts.allowCustom) {
        var raw = input.value.trim();
        if (raw && (!opts.validateCustom || opts.validateCustom(raw))) {
          e.preventDefault();
          add(raw);
        }
      } else if (e.key === "Backspace" && !input.value && selected.length) {
        remove(selected[selected.length - 1]);
      } else if (e.key === "Escape") {
        closeMenu();
      }
    });
    control.addEventListener("mousedown", function (e) {
      if (e.target === control) input.focus();
    });
    document.addEventListener("mousedown", function (e) {
      if (!wrap.contains(e.target)) closeMenu();
    });

    control.appendChild(input);
    wrap.appendChild(control);
    wrap.appendChild(menu);
    renderChips();

    return wrap;
  }

  /* ---------------- markdown editor field ---------------- */

  // A field with "Escrever | Visualizar" tabs so LaTeX renders live in place.
  function markdownField(value, opts) {
    opts = opts || {};
    var wrap = el("div", "mdf");

    var tabs = el("div", "mdf-tabs");
    var writeTab = el("button", "mdf-tab", "Escrever");
    var previewTab = el("button", "mdf-tab", "Visualizar");
    writeTab.type = "button";
    previewTab.type = "button";
    tabs.appendChild(writeTab);
    tabs.appendChild(previewTab);

    var area = el("textarea", "mdf-area");
    area.value = value || "";
    area.placeholder = opts.placeholder || "";
    area.rows = opts.rows || 3;

    var preview = el("div", "mdf-preview md-content");

    function autoResize() {
      area.style.height = "auto";
      area.style.height = area.scrollHeight + 2 + "px";
    }

    function setMode(mode) {
      var writing = mode === "write";
      writeTab.classList.toggle("active", writing);
      previewTab.classList.toggle("active", !writing);
      area.classList.toggle("hidden", !writing);
      preview.classList.toggle("hidden", writing);
      if (writing) {
        autoResize();
        area.focus();
      } else {
        renderMarkdownInto(preview, area.value);
      }
    }

    area.addEventListener("input", function () {
      autoResize();
      opts.onChange && opts.onChange(area.value);
    });
    writeTab.addEventListener("click", function () {
      setMode("write");
    });
    previewTab.addEventListener("click", function () {
      setMode("preview");
    });

    wrap.appendChild(tabs);
    wrap.appendChild(area);
    wrap.appendChild(preview);

    // Start in preview when there's content to read, otherwise in write.
    setMode(value && value.trim() ? "preview" : "write");
    return wrap;
  }

  function gradeInput(value, opts) {
    opts = opts || {};
    var input = el("input", "grade-input");
    input.type = "number";
    input.step = "any";
    input.min = "0";
    input.value = value == null ? "" : value;
    if (opts.placeholder) input.placeholder = opts.placeholder;
    input.addEventListener("input", function () {
      var v = input.value === "" ? null : Number(input.value);
      opts.onChange && opts.onChange(v);
    });
    return input;
  }

  function fieldBlock(labelText) {
    var block = el("div", "review-field");
    block.appendChild(el("span", "review-field-label", labelText));
    return block;
  }

  /* ---------------- review rendering ---------------- */

  function renderReview() {
    renderFileCard();
    renderMeta();
    renderRecToggle();
    renderQuestions();
    updateTotals();
  }

  function renderFileCard() {
    var questoes = prova.questoes || [];
    els.filename.textContent = fileNames.join(", ") || "Arquivo enviado";
    var withAnswers = questoes.filter(function (q) {
      return q.resposta;
    }).length;
    els.filesub.textContent =
      questoes.length +
      " " +
      plural(questoes.length, "questão extraída", "questões extraídas") +
      " · " +
      withAnswers +
      " com gabarito";
  }

  function renderMeta() {
    els.meta.innerHTML = "";

    els.meta.appendChild(
      textMetaField("Matéria", "materia", { wide: true })
    );

    // Professor — chip multiselect (filled once /api/professors/ resolves).
    professorField = el("div", "review-meta-field wide");
    professorField.appendChild(metaLabel("Professor(es)"));
    professorSlot = el("div", "professor-slot");
    professorField.appendChild(professorSlot);
    els.meta.appendChild(professorField);
    renderProfessorField();

    els.meta.appendChild(textMetaField("Ano / Semestre", "ano_semestre"));
    els.meta.appendChild(dateMetaField("Data de aplicação", "data_aplicacao"));
    els.meta.appendChild(
      numberMetaField("Nº da avaliação", "numero_avaliacao", { integer: true, min: 1 })
    );
    els.meta.appendChild(
      numberMetaField("Nota final recebida", "nota_final", {
        placeholder: "em branco se não corrigida",
      })
    );

    // Cursos — chip multiselect from the fixed course list.
    var cursosField = el("div", "review-meta-field wide");
    cursosField.appendChild(metaLabel("Curso(s)"));
    cursosField.appendChild(
      chipMultiSelect({
        selected: prova.cursos,
        options: COURSES.map(function (c) {
          return { value: c, label: c };
        }),
        placeholder: prova.cursos.length ? "" : "Selecione os cursos…",
        emptyHint: "Nenhum curso encontrado",
      })
    );
    els.meta.appendChild(cursosField);
  }

  function metaLabel(text) {
    return el("span", "review-meta-label", text);
  }

  function textMetaField(label, key, opts) {
    opts = opts || {};
    var field = el("div", "review-meta-field" + (opts.wide ? " wide" : ""));
    field.appendChild(metaLabel(label));
    var input = el("input", "meta-input");
    input.type = "text";
    input.value = prova[key] == null ? "" : prova[key];
    input.addEventListener("input", function () {
      prova[key] = input.value;
    });
    field.appendChild(input);
    return field;
  }

  function dateMetaField(label, key) {
    var field = el("div", "review-meta-field");
    field.appendChild(metaLabel(label));
    var input = el("input", "meta-input");
    input.type = "date";
    input.value = prova[key] || "";
    input.addEventListener("input", function () {
      prova[key] = input.value || null;
    });
    field.appendChild(input);
    return field;
  }

  function numberMetaField(label, key, opts) {
    opts = opts || {};
    var field = el("div", "review-meta-field");
    field.appendChild(metaLabel(label));
    var input = el("input", "meta-input");
    input.type = "number";
    input.step = opts.integer ? "1" : "any";
    if (opts.min != null) input.min = String(opts.min);
    if (opts.placeholder) input.placeholder = opts.placeholder;
    input.value = prova[key] == null ? "" : prova[key];
    input.addEventListener("input", function () {
      if (input.value === "") {
        prova[key] = null;
      } else {
        prova[key] = opts.integer
          ? parseInt(input.value, 10)
          : Number(input.value);
      }
    });
    field.appendChild(input);
    return field;
  }

  var professorField = null;
  var professorSlot = null;

  function renderProfessorField() {
    if (!professorSlot) return;
    professorSlot.innerHTML = "";

    if (profHint) {
      var hint = el("div", "prof-hint");
      hint.appendChild(
        el("span", "prof-hint-text", "A IA leu “" + profHint + "” — confirme o e-mail.")
      );
      professorSlot.appendChild(hint);
    }

    professorSlot.appendChild(
      chipMultiSelect({
        selected: prova.professor,
        options: teachers.map(function (t) {
          return { value: t.email, label: t.name, sub: t.email };
        }),
        placeholder: prova.professor.length
          ? "adicionar outro…"
          : "Busque por nome ou digite um e-mail @uffs.edu.br",
        allowCustom: true,
        validateCustom: isUffsEmail,
        customHint: "E-mail precisa terminar em " + UFFS_DOMAIN,
        emptyHint: teachers.length
          ? "Nenhum professor encontrado"
          : "Sem cache de professores — digite o e-mail @uffs.edu.br",
        onChange: function () {
          if (prova.professor.length && profHint) {
            profHint = "";
            renderProfessorField();
          }
        },
      })
    );
  }

  function isUffsEmail(value) {
    return /^[^\s@]+@uffs\.edu\.br$/i.test(value.trim());
  }

  function renderRecToggle() {
    var on = !!prova.recuperacao;
    els.recToggle.classList.toggle("checked", on);
    els.recToggle.setAttribute("aria-checked", String(on));
  }

  /* ---------------- questions ---------------- */

  function hasSubs(q) {
    return Array.isArray(q.subquestoes) && q.subquestoes.length > 0;
  }

  function sumBy(list, key) {
    return list.reduce(function (acc, item) {
      return acc + (Number(item[key]) || 0);
    }, 0);
  }

  // For questions with subquestões the parent points/grade are derived sums.
  function effectivePontuacao(q) {
    return hasSubs(q) ? sumBy(q.subquestoes, "pontuacao") : Number(q.pontuacao) || 0;
  }
  function effectiveNota(q) {
    if (hasSubs(q)) {
      var any = q.subquestoes.some(function (s) {
        return s.nota_recebida != null;
      });
      return any ? sumBy(q.subquestoes, "nota_recebida") : null;
    }
    return q.nota_recebida;
  }

  function renderQuestions() {
    var questoes = prova.questoes || [];
    els.questionsCount.textContent =
      "Questões (" + questoes.length + ")";
    els.questions.innerHTML = "";

    questoes.forEach(function (q, idx) {
      els.questions.appendChild(questionCard(q, idx));
    });

    var add = el("button", "review-add-question");
    add.type = "button";
    add.innerHTML =
      '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg> Adicionar questão manualmente';
    add.addEventListener("click", addQuestion);
    els.questions.appendChild(add);
  }

  function questionCard(q, idx) {
    var card = el("div", "review-question-card");

    /* header */
    var head = el("div", "review-question-head");
    var ptsBadge = el("span", "review-question-pts");
    head.appendChild(ptsBadge);

    var tag = el("span", "review-question-tag");
    tag.innerHTML =
      '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>' +
      (q.resposta ? "com gabarito" : "sem gabarito");
    head.appendChild(tag);

    var del = el("button", "review-icon-btn", "");
    del.type = "button";
    del.title = "Remover questão";
    del.innerHTML =
      '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/></svg>';
    del.addEventListener("click", function () {
      prova.questoes.splice(idx, 1);
      renderQuestions();
      updateTotals();
    });
    head.appendChild(del);
    card.appendChild(head);

    /* enunciado */
    var enunBlock = fieldBlock("Enunciado");
    enunBlock.appendChild(
      markdownField(q.enunciado, {
        placeholder: "Enunciado da questão (Markdown + LaTeX: $x^2$)",
        rows: 3,
        onChange: function (v) {
          q.enunciado = v;
        },
      })
    );
    card.appendChild(enunBlock);

    /* grades row (only when there are no subquestões) */
    var gradeRow = el("div", "review-grade-row");
    function renderGradeRow() {
      gradeRow.innerHTML = "";
      if (hasSubs(q)) {
        var note = el(
          "div",
          "review-grade-note",
          "Pontuação e nota são a soma das subquestões."
        );
        gradeRow.appendChild(note);
      } else {
        var ptsField = el("div", "review-grade-field");
        ptsField.appendChild(el("span", "review-field-label", "Pontuação"));
        ptsField.appendChild(
          gradeInput(q.pontuacao, {
            placeholder: "0",
            onChange: function (v) {
              q.pontuacao = v;
              refreshBadges();
              updateTotals();
            },
          })
        );
        gradeRow.appendChild(ptsField);

        var notaField = el("div", "review-grade-field");
        notaField.appendChild(el("span", "review-field-label", "Nota recebida"));
        notaField.appendChild(
          gradeInput(q.nota_recebida, {
            placeholder: "em branco",
            onChange: function (v) {
              q.nota_recebida = v;
              refreshBadges();
              updateTotals();
            },
          })
        );
        gradeRow.appendChild(notaField);
      }
    }
    renderGradeRow();
    card.appendChild(gradeRow);

    /* resposta (only when there are no subquestões — they carry their own) */
    var respBlock = el("div", "review-field hidden");
    function renderRespBlock() {
      respBlock.innerHTML = "";
      respBlock.classList.toggle("hidden", hasSubs(q));
      if (hasSubs(q)) return;
      respBlock.appendChild(el("span", "review-field-label", "Resposta / gabarito"));
      respBlock.appendChild(
        markdownField(q.resposta || "", {
          placeholder: "Resolução esperada (opcional)",
          rows: 3,
          onChange: function (v) {
            q.resposta = v.trim() ? v : null;
            tag.lastChild && (tag.childNodes[tag.childNodes.length - 1].textContent =
              q.resposta ? "com gabarito" : "sem gabarito");
          },
        })
      );
    }
    renderRespBlock();
    card.appendChild(respBlock);

    /* subquestões */
    var subsWrap = el("div", "review-subs");
    function renderSubs() {
      subsWrap.innerHTML = "";
      q.subquestoes.forEach(function (sub, sidx) {
        subsWrap.appendChild(subCard(q, sub, sidx, function () {
          refreshBadges();
          updateTotals();
        }));
      });
      var addSub = el("button", "review-add-sub");
      addSub.type = "button";
      addSub.innerHTML =
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg> Adicionar subquestão';
      addSub.addEventListener("click", function () {
        q.subquestoes.push(newSubquestao());
        renderSubs();
        renderGradeRow();
        renderRespBlock();
        refreshBadges();
        updateTotals();
      });
      subsWrap.appendChild(addSub);
    }
    renderSubs();
    card.appendChild(subsWrap);

    function refreshBadges() {
      ptsBadge.textContent = fmtPts(effectivePontuacao(q)) + " pts";
    }
    // expose so subCard deletion can re-render the parent grade row / resp block
    card._renderGradeRow = renderGradeRow;
    card._renderRespBlock = renderRespBlock;
    card._renderSubs = renderSubs;
    refreshBadges();

    return card;
  }

  function subCard(q, sub, sidx, onGradeChange) {
    var wrap = el("div", "review-sub-card");

    var head = el("div", "review-sub-head");

    var del = el("button", "review-icon-btn", "");
    del.type = "button";
    del.title = "Remover subquestão";
    del.innerHTML =
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/></svg>';
    del.addEventListener("click", function () {
      q.subquestoes.splice(sidx, 1);
      // Re-render the whole card's subs + grade row + resp block via parent helpers.
      var card = wrap.closest(".review-question-card");
      if (card && card._renderSubs) card._renderSubs();
      if (card && card._renderGradeRow) card._renderGradeRow();
      if (card && card._renderRespBlock) card._renderRespBlock();
      onGradeChange && onGradeChange();
    });
    head.appendChild(del);
    wrap.appendChild(head);

    var enunBlock = fieldBlock("Enunciado");
    enunBlock.appendChild(
      markdownField(sub.enunciado, {
        placeholder: "Enunciado da subquestão (Markdown + LaTeX)",
        rows: 2,
        onChange: function (v) {
          sub.enunciado = v;
        },
      })
    );
    wrap.appendChild(enunBlock);

    var gradeRow = el("div", "review-grade-row");
    var ptsField = el("div", "review-grade-field");
    ptsField.appendChild(el("span", "review-field-label", "Pontuação"));
    ptsField.appendChild(
      gradeInput(sub.pontuacao, {
        placeholder: "0",
        onChange: function (v) {
          sub.pontuacao = v;
          onGradeChange && onGradeChange();
        },
      })
    );
    gradeRow.appendChild(ptsField);

    var notaField = el("div", "review-grade-field");
    notaField.appendChild(el("span", "review-field-label", "Nota recebida"));
    notaField.appendChild(
      gradeInput(sub.nota_recebida, {
        placeholder: "em branco",
        onChange: function (v) {
          sub.nota_recebida = v;
          onGradeChange && onGradeChange();
        },
      })
    );
    gradeRow.appendChild(notaField);
    wrap.appendChild(gradeRow);

    var respBlock = fieldBlock("Resposta / gabarito");
    respBlock.appendChild(
      markdownField(sub.resposta || "", {
        placeholder: "Resolução esperada (opcional)",
        rows: 2,
        onChange: function (v) {
          sub.resposta = v.trim() ? v : null;
        },
      })
    );
    wrap.appendChild(respBlock);

    return wrap;
  }

  function newSubquestao() {
    return {
      enunciado: "",
      pontuacao: 0,
      resposta: null,
      nota_recebida: null,
    };
  }

  function addQuestion() {
    prova.questoes.push({
      enunciado: "",
      pontuacao: 0,
      resposta: null,
      nota_recebida: null,
      subquestoes: [],
    });
    renderQuestions();
    updateTotals();
    var cards = els.questions.querySelectorAll(".review-question-card");
    var last = cards[cards.length - 1];
    if (last) last.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function updateTotals() {
    var questoes = prova.questoes || [];
    var total = questoes.reduce(function (sum, q) {
      return sum + effectivePontuacao(q);
    }, 0);
    els.questionsTotal.textContent = total ? fmtPts(total) + " pts no total" : "";

    els.footerText.textContent =
      questoes.length +
      " " +
      plural(questoes.length, "questão pronta", "questões prontas") +
      " para indexação no banco.";
  }

  /* ---------------- save ---------------- */

  function save() {
    if (saving || !prova) return;
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
    teachers = [];
    profHint = "";
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
      if (els.fileInput.files.length) startExtraction(els.fileInput.files);
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

  // Exposed for manual testing without spending OCR budget.
  window.__pgUpload = {
    inject: function (data, names) {
      prova = data.prova || data;
      fileNames = names || data.file_names || ["teste.pdf"];
      enterReview();
    },
  };
})();
