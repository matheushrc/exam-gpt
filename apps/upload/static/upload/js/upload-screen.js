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

  // Highly efficient O(N) subsequence and overlap string similarity score function
  function getSimilarityScore(str, query) {
    str = str.toLowerCase();
    query = query.toLowerCase();
    
    if (str === query) return 1.0;
    if (str.indexOf(query) === 0) return 0.8 + (query.length / str.length) * 0.19;
    
    var idx = str.indexOf(query);
    if (idx !== -1) return 0.6 + (query.length / str.length) * 0.19;
    
    var queryIdx = 0;
    var matches = 0;
    var gaps = 0;
    for (var i = 0; i < str.length; i++) {
      if (str[i] === query[queryIdx]) {
        queryIdx++;
        matches++;
        if (queryIdx === query.length) break;
      } else if (queryIdx > 0) {
        gaps++;
      }
    }
    
    if (matches === query.length) {
      return 0.4 + (query.length / (query.length + gaps)) * 0.19;
    }
    
    var set1 = {};
    var set2 = {};
    for (var j = 0; j < str.length; j++) set1[str[j]] = true;
    for (var k = 0; k < query.length; k++) set2[query[k]] = true;
    var intersection = 0;
    for (var key in set2) {
      if (set1[key]) intersection++;
    }
    
    if (intersection > 0) {
      return (intersection / Math.max(str.length, query.length)) * 0.3;
    }
    
    return 0.0;
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

  // First line of the enunciado for the collapsed-row preview (CSS truncates
  // with ellipsis; this just strips to one line and avoids rendering Markdown).
  function firstLine(text) {
    return String(text == null ? "" : text).split("\n")[0].trim();
  }

  // Presentational position labels — derived from list index at render time,
  // never persisted or sent in the payload. Questions: 1, 2, 3…; subs: a, b, c…
  function qIndexLabel(idx) {
    return String(idx + 1);
  }
  function subIndexLabel(idx) {
    var n = idx + 1;
    var s = "";
    while (n > 0) {
      n--;
      s = String.fromCharCode(97 + (n % 26)) + s;
      n = Math.floor(n / 26);
    }
    return s;
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

  function loadTeachers() {
    var semester = prova.ano_semestre || "";
    var url = "/api/professors/";
    if (semester) url += "?semester=" + encodeURIComponent(semester);

    fetch(url)
      .then(function (r) {
        return r.ok ? r.json() : [];
      })
      .then(function (list) {
        var seen = {};
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
          })
          .filter(function (t) {
            var key = t.name.toLowerCase() + "|" + t.email.toLowerCase();
            if (seen[key]) return false;
            seen[key] = true;
            return true;
          });
        teachers.sort(function (a, b) {
          return a.name.localeCompare(b.name, "pt-BR", { sensitivity: "base" });
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
      var username = (t.username || "").toLowerCase();
      return name === hint || name.indexOf(hint) !== -1 || hint.indexOf(name) !== -1 || username === hint;
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
        return selected.indexOf(o.value) === -1;
      });

      if (!q) {
        available = available.slice(0, 5);
      } else {
        available = available
          .map(function (o) {
            var labelScore = getSimilarityScore(o.label, q);
            var subScore = getSimilarityScore(o.sub || "", q);
            o.score = Math.max(labelScore, subScore);
            return o;
          })
          .filter(function (o) {
            return o.score > 0;
          })
          .sort(function (a, b) {
            if (b.score !== a.score) return b.score - a.score;
            return a.label.localeCompare(b.label, "pt-BR", { sensitivity: "base" });
          });
      }

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
      // Skip while the field sits inside a collapsed (display:none) card:
      // scrollHeight is 0 there, which would pin the textarea to ~2px. The
      // `rows` attribute governs the height until the field is visible and the
      // user focuses/types it (see the focus handler below).
      if (area.offsetParent === null) return;
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
    // Fit the height to existing content the first time the field is entered —
    // it may have been built while hidden (collapsed card), where autoResize
    // bails, so it still shows the `rows` default until now.
    area.addEventListener("focus", autoResize);
    writeTab.addEventListener("click", function () {
      setMode("write");
    });
    previewTab.addEventListener("click", function () {
      setMode("preview");
    });

    wrap.appendChild(tabs);
    wrap.appendChild(area);
    wrap.appendChild(preview);

    // Always start in write mode so enunciado/resposta fields open ready to
    // edit; the user switches to "Visualizar" on demand.
    setMode("write");
    return wrap;
  }

  function gradeInput(value, opts) {
    opts = opts || {};
    var input = el("input", "grade-input");
    input.type = "text";
    input.value = value == null ? "" : String(value).replace(".", ",");
    if (opts.placeholder) input.placeholder = opts.placeholder;
    input.addEventListener("input", function () {
      var val = input.value.replace(/\./g, ",");
      val = val.replace(/[^0-9,]/g, "");
      var parts = val.split(",");
      if (parts.length > 2) {
        val = parts[0] + "," + parts.slice(1).join("");
      }
      input.value = val;
      var v = val === "" ? null : Number(val.replace(",", "."));
      if (isNaN(v)) v = null;
      opts.onChange && opts.onChange(v);
    });
    return input;
  }

  function fieldBlock(labelText) {
    var block = el("div", "review-field");
    block.appendChild(el("span", "review-field-label", labelText));
    return block;
  }

  /* ---------------- drag-to-reorder (pointer events) ---------------- */

  // Builds the 6-dot grip button shared by question/sub headers.
  function gripButton(title) {
    var grip = el("button", "review-icon-btn review-grip", "");
    grip.type = "button";
    grip.title = title;
    grip.innerHTML =
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">' +
      '<circle cx="9" cy="5" r="1.5"/><circle cx="9" cy="12" r="1.5"/><circle cx="9" cy="19" r="1.5"/>' +
      '<circle cx="15" cy="5" r="1.5"/><circle cx="15" cy="12" r="1.5"/><circle cx="15" cy="19" r="1.5"/>' +
      "</svg>";
    return grip;
  }

  // Wires pointer-based drag-to-reorder onto `grip` for `card`, scoped to the
  // sibling elements matching `cardClass` inside `container`. `getList` returns
  // the live array backing the rendered cards (e.g. prova.questoes, or a given
  // question's subquestoes); `onReorder` triggers the full re-render after the
  // array is spliced. Index computation only ever considers `container`'s
  // `cardClass` children, so a sub's drag never sees another question's subs
  // and a question's drag never sees a sub list — the scope is fixed at the
  // call site below, not discovered at drag time.
  function enableDragReorder(opts) {
    var grip = opts.grip;
    var card = opts.card;
    // `container` may be the element itself, or a function returning it —
    // sub cards aren't appended to their `.review-subs` wrap until after
    // `subCard()` returns, so they pass a function resolved lazily at drag
    // time once the card is definitely in the DOM.
    var getContainer =
      typeof opts.container === "function" ? opts.container : function () {
        return opts.container;
      };
    var cardClass = opts.cardClass;
    var getList = opts.getList;
    var onReorder = opts.onReorder;

    var dragging = false;
    var pointerId = null;
    var startY = 0;
    var startIndex = -1;
    var cardHeight = 0;
    // Other cards in container, excluding the dragged one, sorted by their
    // original top position (their order before the drag started).
    var siblingsByOrder = [];

    function cardsInContainer() {
      var container = getContainer();
      if (!container) return [];
      return Array.prototype.slice
        .call(container.children)
        .filter(function (node) {
          return node.classList && node.classList.contains(cardClass);
        });
    }

    function clearTransforms() {
      card.style.transform = "";
      siblingsByOrder.forEach(function (s) {
        s.el.style.transform = "";
      });
    }

    // Number of siblings whose original midpoint sits above `currentY` —
    // i.e. the final index the dragged card would occupy if dropped there.
    function computeTargetIndex(currentY) {
      var above = 0;
      siblingsByOrder.forEach(function (s) {
        if (s.mid < currentY) above++;
      });
      return above;
    }

    function onPointerDown(e) {
      if (dragging) return;
      e.preventDefault();
      var all = cardsInContainer();
      startIndex = all.indexOf(card);
      if (startIndex === -1) return;

      dragging = true;
      pointerId = e.pointerId;
      startY = e.clientY;
      cardHeight = card.getBoundingClientRect().height;
      siblingsByOrder = all
        .filter(function (node) {
          return node !== card;
        })
        .map(function (node) {
          var rect = node.getBoundingClientRect();
          return { el: node, top: rect.top, mid: rect.top + rect.height / 2 };
        })
        .sort(function (a, b) {
          return a.top - b.top;
        });

      try {
        grip.setPointerCapture(pointerId);
      } catch (err) {
        // ignore — some browsers may not support capture on the grip element
      }
      card.classList.add("dragging");

      grip.addEventListener("pointermove", onPointerMove);
      grip.addEventListener("pointerup", onPointerUp);
      grip.addEventListener("pointercancel", onPointerUp);
    }

    function onPointerMove(e) {
      if (!dragging) return;
      var dy = e.clientY - startY;
      card.style.transform = "translateY(" + dy + "px)";

      // Preview the gap: siblings that the dragged card has moved past shift
      // by one card-height to make room.
      var targetIndex = computeTargetIndex(e.clientY);
      siblingsByOrder.forEach(function (s, pos) {
        var shift = 0;
        if (pos >= targetIndex && pos < startIndex) {
          shift = cardHeight;
        } else if (pos < targetIndex && pos >= startIndex) {
          shift = -cardHeight;
        }
        s.el.style.transform = shift ? "translateY(" + shift + "px)" : "";
      });
    }

    function onPointerUp(e) {
      if (!dragging) return;
      dragging = false;
      try {
        grip.releasePointerCapture(pointerId);
      } catch (err) {
        // ignore
      }
      grip.removeEventListener("pointermove", onPointerMove);
      grip.removeEventListener("pointerup", onPointerUp);
      grip.removeEventListener("pointercancel", onPointerUp);
      card.classList.remove("dragging");

      var targetIndex = computeTargetIndex(e.clientY);
      clearTransforms();

      if (targetIndex !== startIndex) {
        var list = getList();
        var item = list.splice(startIndex, 1)[0];
        list.splice(targetIndex, 0, item);
        onReorder();
      }
    }

    grip.addEventListener("pointerdown", onPointerDown);
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
        placeholder: "9,5",
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
    if (key === "nota_final") {
      input.type = "text";
      if (opts.placeholder) input.placeholder = opts.placeholder;
      input.value = prova[key] == null ? "" : String(prova[key]).replace(".", ",");
      input.addEventListener("input", function () {
        var val = input.value.replace(/\./g, ",");
        val = val.replace(/[^0-9,]/g, "");
        var parts = val.split(",");
        if (parts.length > 2) {
          val = parts[0] + "," + parts.slice(1).join("");
        }
        input.value = val;
        var v = val === "" ? null : Number(val.replace(",", "."));
        if (isNaN(v)) v = null;
        prova[key] = v;
      });
    } else {
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
    }
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

    /* ── header: clickable summary row ── */
    var head = el("div", "review-question-head");

    var grip = gripButton("Arrastar para reordenar");
    head.appendChild(grip);

    var index = el("span", "review-q-index", qIndexLabel(idx));
    head.appendChild(index);

    var preview = el("span", "review-q-preview");
    head.appendChild(preview);

    var meta = el("div", "review-q-meta");

    // gabarito check (hidden when the question has subquestões — subs carry
    // their own answers)
    var tag = el("span", "review-question-tag");
    tag.innerHTML =
      '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>';

    // collapsed read-only grade badge ("pts / nota")
    var badge = el("span", "review-question-pts");

    // expanded inline grade inputs (built lazily on first expand)
    var headGrades = el("div", "review-head-grade hidden");
    var headGradesBuilt = false;
    function buildHeadGrades() {
      if (headGradesBuilt) return;
      headGradesBuilt = true;
      var ptsWrap = el("label", "review-grade-num");
      ptsWrap.appendChild(el("span", "review-grade-num-label", "pts"));
      ptsWrap.appendChild(
        gradeInput(q.pontuacao, {
          placeholder: "9,5",
          onChange: function (v) {
            q.pontuacao = v;
            renderHeadMeta();
            updateTotals();
          },
        })
      );
      var notaWrap = el("label", "review-grade-num");
      notaWrap.appendChild(el("span", "review-grade-num-label", "nota"));
      notaWrap.appendChild(
        gradeInput(q.nota_recebida, {
          placeholder: "—",
          onChange: function (v) {
            q.nota_recebida = v;
            renderHeadMeta();
            updateTotals();
          },
        })
      );
      headGrades.appendChild(ptsWrap);
      headGrades.appendChild(notaWrap);
    }

    var del = el("button", "review-icon-btn", "");
    del.type = "button";
    del.title = "Remover questão";
    del.innerHTML =
      '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/></svg>';
    del.addEventListener("click", function (e) {
      e.stopPropagation();
      prova.questoes.splice(idx, 1);
      renderQuestions();
      updateTotals();
    });

    var caret = el("span", "review-q-caret");
    caret.innerHTML =
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"/></svg>';

    meta.appendChild(tag);
    meta.appendChild(badge);
    meta.appendChild(headGrades);
    meta.appendChild(del);
    meta.appendChild(caret);
    head.appendChild(meta);
    card.appendChild(head);

    // grip and grade inputs must never toggle the card open/closed.
    grip.addEventListener("click", function (e) {
      e.stopPropagation();
    });
    headGrades.addEventListener("click", function (e) {
      e.stopPropagation();
    });
    headGrades.addEventListener("pointerdown", function (e) {
      e.stopPropagation();
    });
    head.addEventListener("click", function () {
      toggleOpen();
    });

    enableDragReorder({
      grip: grip,
      card: card,
      container: els.questions,
      cardClass: "review-question-card",
      getList: function () {
        return prova.questoes;
      },
      onReorder: renderQuestions,
    });

    /* ── body: 2-column editor grid + subnote + subs ── */
    var body = el("div", "review-question-body");

    var grid = el("div", "review-editor-grid");

    var enunBlock = fieldBlock("Enunciado");
    enunBlock.appendChild(
      markdownField(q.enunciado, {
        placeholder: "Enunciado da questão (Markdown + LaTeX: $x^2$)",
        rows: 3,
        onChange: function (v) {
          q.enunciado = v;
          renderPreview();
        },
      })
    );
    grid.appendChild(enunBlock);

    // resposta (hidden when there are subquestões — they carry their own)
    var respBlock = el("div", "review-field hidden");
    function renderRespBlock() {
      respBlock.innerHTML = "";
      respBlock.classList.toggle("hidden", hasSubs(q));
      if (hasSubs(q)) return;
      respBlock.appendChild(
        el("span", "review-field-label", "Resposta / gabarito")
      );
      respBlock.appendChild(
        markdownField(q.resposta || "", {
          placeholder: "Resolução esperada (opcional)",
          rows: 3,
          onChange: function (v) {
            q.resposta = v.trim() ? v : null;
            renderHeadMeta();
          },
        })
      );
    }
    renderRespBlock();
    grid.appendChild(respBlock);
    body.appendChild(grid);

    var subnote = el(
      "div",
      "review-grade-note hidden",
      "Pontuação e nota são a soma das subquestões."
    );
    body.appendChild(subnote);

    var subsWrap = el("div", "review-subs");
    function renderSubs() {
      subsWrap.innerHTML = "";
      q.subquestoes.forEach(function (sub, sidx) {
        subsWrap.appendChild(
          subCard(q, sub, sidx, function () {
            renderHeadMeta();
            updateTotals();
          })
        );
      });
      var addSub = el("button", "review-add-sub");
      addSub.type = "button";
      addSub.innerHTML =
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg> Adicionar subquestão';
      addSub.addEventListener("click", function () {
        q.subquestoes.push(newSubquestao());
        renderSubs();
        renderRespBlock();
        renderHeadMeta();
        updateTotals();
      });
      subsWrap.appendChild(addSub);
    }
    renderSubs();
    body.appendChild(subsWrap);

    card.appendChild(body);

    /* ── state ── */
    function renderPreview() {
      var text = firstLine(q.enunciado);
      preview.textContent = text || "Sem enunciado";
      preview.classList.toggle("review-q-preview-empty", !text);
    }

    function renderHeadMeta() {
      var subs = hasSubs(q);
      var open = card.classList.contains("is-open");

      // gabarito check — only when no subs
      tag.classList.toggle("hidden", subs || !q.resposta);

      // badge always reflects effective pts / nota (sum when subs)
      var nota = effectiveNota(q);
      badge.textContent =
        fmtPts(effectivePontuacao(q)) +
        " / " +
        (nota == null ? "—" : fmtPts(nota));

      // inline inputs only when expanded AND no subs; badge otherwise
      var showInputs = open && !subs;
      if (showInputs) buildHeadGrades();
      headGrades.classList.toggle("hidden", !showInputs);
      badge.classList.toggle("hidden", showInputs);

      // subnote only when subs
      subnote.classList.toggle("hidden", !subs);
    }

    function toggleOpen() {
      card.classList.toggle("is-open");
      renderHeadMeta();
    }

    // expose for subCard add/delete to refresh parent head + resp + subs
    card._renderHeadMeta = renderHeadMeta;
    card._renderRespBlock = renderRespBlock;
    card._renderSubs = renderSubs;

    renderPreview();
    renderHeadMeta();

    return card;
  }

  function subCard(q, sub, sidx, onGradeChange) {
    var wrap = el("div", "review-sub-card");

    /* ── header summary row ── */
    var head = el("div", "review-sub-head");

    var grip = gripButton("Arrastar para reordenar");
    head.appendChild(grip);

    var index = el("span", "review-q-index review-sub-index", subIndexLabel(sidx));
    head.appendChild(index);

    var preview = el("span", "review-q-preview");
    head.appendChild(preview);

    var meta = el("div", "review-q-meta");

    var badge = el("span", "review-question-pts");

    var headGrades = el("div", "review-head-grade hidden");
    var headGradesBuilt = false;
    function buildHeadGrades() {
      if (headGradesBuilt) return;
      headGradesBuilt = true;
      var ptsWrap = el("label", "review-grade-num");
      ptsWrap.appendChild(el("span", "review-grade-num-label", "pts"));
      ptsWrap.appendChild(
        gradeInput(sub.pontuacao, {
          placeholder: "9,5",
          onChange: function (v) {
            sub.pontuacao = v;
            renderHeadMeta();
            onGradeChange && onGradeChange();
          },
        })
      );
      var notaWrap = el("label", "review-grade-num");
      notaWrap.appendChild(el("span", "review-grade-num-label", "nota"));
      notaWrap.appendChild(
        gradeInput(sub.nota_recebida, {
          placeholder: "—",
          onChange: function (v) {
            sub.nota_recebida = v;
            renderHeadMeta();
            onGradeChange && onGradeChange();
          },
        })
      );
      headGrades.appendChild(ptsWrap);
      headGrades.appendChild(notaWrap);
    }

    var del = el("button", "review-icon-btn", "");
    del.type = "button";
    del.title = "Remover subquestão";
    del.innerHTML =
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/></svg>';
    del.addEventListener("click", function (e) {
      e.stopPropagation();
      q.subquestoes.splice(sidx, 1);
      var card = wrap.closest(".review-question-card");
      if (card && card._renderSubs) card._renderSubs();
      if (card && card._renderRespBlock) card._renderRespBlock();
      if (card && card._renderHeadMeta) card._renderHeadMeta();
      onGradeChange && onGradeChange();
    });

    var caret = el("span", "review-q-caret");
    caret.innerHTML =
      '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"/></svg>';

    meta.appendChild(badge);
    meta.appendChild(headGrades);
    meta.appendChild(del);
    meta.appendChild(caret);
    head.appendChild(meta);
    wrap.appendChild(head);

    grip.addEventListener("click", function (e) {
      e.stopPropagation();
    });
    headGrades.addEventListener("click", function (e) {
      e.stopPropagation();
    });
    headGrades.addEventListener("pointerdown", function (e) {
      e.stopPropagation();
    });
    head.addEventListener("click", function () {
      toggleOpen();
    });

    enableDragReorder({
      grip: grip,
      card: wrap,
      container: function () {
        return wrap.parentElement;
      },
      cardClass: "review-sub-card",
      getList: function () {
        return q.subquestoes;
      },
      onReorder: function () {
        var ownerCard = wrap.closest(".review-question-card");
        if (ownerCard && ownerCard._renderSubs) ownerCard._renderSubs();
      },
    });

    /* ── body: 2-column editor grid ── */
    var body = el("div", "review-question-body review-sub-body");
    var grid = el("div", "review-editor-grid");

    var enunBlock = fieldBlock("Enunciado");
    enunBlock.appendChild(
      markdownField(sub.enunciado, {
        placeholder: "Enunciado da subquestão (Markdown + LaTeX)",
        rows: 2,
        onChange: function (v) {
          sub.enunciado = v;
          renderPreview();
        },
      })
    );
    grid.appendChild(enunBlock);

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
    grid.appendChild(respBlock);
    body.appendChild(grid);
    wrap.appendChild(body);

    /* ── state ── */
    function renderPreview() {
      var text = firstLine(sub.enunciado);
      preview.textContent = text || "Sem enunciado";
      preview.classList.toggle("review-q-preview-empty", !text);
    }

    function renderHeadMeta() {
      var open = wrap.classList.contains("is-open");
      var nota = sub.nota_recebida;
      badge.textContent =
        fmtPts(sub.pontuacao) + " / " + (nota == null ? "—" : fmtPts(nota));
      if (open) buildHeadGrades();
      headGrades.classList.toggle("hidden", !open);
      badge.classList.toggle("hidden", open);
    }

    function toggleOpen() {
      wrap.classList.toggle("is-open");
      renderHeadMeta();
    }

    renderPreview();
    renderHeadMeta();

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
    if (last) {
      last.classList.add("is-open");
      if (last._renderHeadMeta) last._renderHeadMeta();
      last.scrollIntoView({ behavior: "smooth", block: "center" });
    }
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
