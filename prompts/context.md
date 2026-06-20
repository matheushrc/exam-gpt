# Provas GPT — Implementation Plan

> **Status:** Pronto para implementação. Todas as confirmações (C1–C8) resolvidas — ver `steps/00-confirmations.md`.
> All code targets Python 3.14 / Django 6 / MongoDB via `django-mongodb-backend`.

---

## Decisões Confirmadas

| #   | Decisão                                                                                      |
| --- | -------------------------------------------------------------------------------------------- |
| C1  | `ano_semestre = CharField(max_length=7)` com padrão `"2026.1"` — merge de `ano` + `semestre` |
| C2  | `nota_final` em Prova + `nota_recebida` em Questao + `nota_recebida` em SubQuestão (JSON)    |
| C3  | `recuperacao = BooleanField` apenas — **sem FK** para prova original                         |
| C4  | RAG + geração Gemini: `gemini-3.5-flash` para extração, `gemini-3.1-flash-lite` para chat    |
| C5  | Cache UFFS em disco: `cache/schedule/` (gitignored)                                          |
| C6  | Upload wizard em `apps/upload` separado                                                      |
| C7  | Async Django view para extração no upload                                                    |
| C8  | HTMX filtra professor por matéria via `/upload/api/professors/`                              |

---

## Overview

This plan covers four parallel workstreams that together deliver:

1. **Three-step mobile upload wizard** — capture/select exam images → fill metadata → review questions
2. **Web chat interface** — Claude/ChatGPT-inspired sidebar + RAG-backed chat
3. **Data model evolution** — grades per question/exam, merged semester field, recuperação linkage
4. **Infrastructure** — UFFS API cache, `get_exam_json.py` migration, `schedule → chat` rename

---

## Wireframe Summary (from `design.excalidraw`)

| #   | Platform | Description                                                                                                                                     |
| --- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Mobile   | Upload: camera capture, gallery, PDF; image preview grid; "multi select pictures"                                                               |
| 2   | Mobile   | Metadata form: professor (multiselect), cursos (multiselect), ano_semestre, materia, nº prova + recuperação, nota_final, data_aplicação, salvar |
| 3   | Mobile   | Question review: id / enunciado / resposta rendered as Markdown+LaTeX; expandable text area per field                                           |
| 4   | Web      | Left sidebar (collapse → icon rail with upload + chat icons); main chat area; RAG-powered responses                                             |

---

## Execução com Yume (4 agentes paralelos)

> Yume spawn 4 agentes simultâneos em branches/worktrees isolados.
> Os tipos de agente do Yume mapeiam diretamente nos steps abaixo.

### Wave 1 — Rodar em paralelo (nenhuma dependência entre eles)

| Agente Yume       | Step                             | Prompt de entrada                                                                                                                            |
| ----------------- | -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **Implementer A** | Step 01 — Models & Migrations    | `Leia steps/01-models-migrations.md e execute todos os itens do checklist`                                                                   |
| **Implementer B** | Step 02 — Schedule → Chat rename | `Leia steps/02-schedule-to-chat.md e execute todos os itens do checklist`                                                                    |
| **Implementer C** | Step 03 — UFFS API cache         | `Leia steps/03-uffs-api-cache.md e execute todos os itens do checklist`                                                                      |
| **Explorer**      | Reconhecimento para steps 04–07  | `Leia context.md e os steps 04–07. Mapeie todos os arquivos que cada step vai tocar e gere um relatório de conflitos potenciais entre waves` |

> Merge branches da wave 1 antes de começar a wave 2.

---

### Wave 2 — Rodar após merge da wave 1

| Agente Yume       | Step                                | Prompt de entrada                                                                                             |
| ----------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| **Architect**     | Step 04 — extract migration         | `Leia steps/04-extract-exams-migration.md e execute todos os itens do checklist`                              |
| **Implementer A** | Step 05 Agent A — Upload views      | `Leia steps/05-upload-wizard.md, seções AGENT A (5.3–5.6). Implemente views, session.py e URL wiring`         |
| **Implementer B** | Step 05 Agents B+C — Templates + JS | `Leia steps/05-upload-wizard.md, seções AGENT B (5.7–5.9) e AGENT C (5.10–5.11). Implemente templates e JS`   |
| **Implementer C** | Step 06 Agent A — Chat views        | `Leia steps/06-chat-interface.md, seção AGENT A (6.1–6.3). Implemente ChatView, ChatMessageView e URL wiring` |

> Merge branches da wave 2 antes de começar a wave 3.

---

### Wave 3 — Finalização

| Agente Yume       | Step                             | Prompt de entrada                                                                                                       |
| ----------------- | -------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| **Implementer A** | Step 06 Agent B — Chat templates | `Leia steps/06-chat-interface.md, seção AGENT B (6.4–6.6). Implemente chat.html, chat.js e chat.css`                    |
| **Implementer B** | Step 07 — Frontend design system | `Leia steps/07-frontend-design.md e execute todos os itens do checklist`                                                |
| **Guardian**      | Verificação final                | `Rode uv run python manage.py test, uv run ruff check . e uv run djlint templates apps --check. Reporte todos os erros` |
| **Explorer**      | Documentação                     | `Atualize AGENTS.md com os novos comandos e apps adicionados nas waves 1–3`                                             |

---

### Dicas para uso no Yume

- Cada agente deve **começar lendo o `AGENTS.md`** do projeto — ele já tem as convenções e comandos.
- O **Explorer da wave 1** é importante: identifica conflitos antes que os Implementers batam cabeça (ex: dois agentes tocando `settings/urls.py` ao mesmo tempo).
- Use **worktrees isolados** (não apenas branches) para wave 1 e 2 — evita conflitos de lock do MongoDB em testes paralelos.
- O **Guardian na wave 3** deve rodar `docker compose up mongo -d` antes dos testes para garantir que o banco está disponível.
- Prefixo de commit sugerido por wave: `wave1/`, `wave2/`, `wave3/` para facilitar o rebase.

| File                                  | Scope                                                                        | Agents           |
| ------------------------------------- | ---------------------------------------------------------------------------- | ---------------- |
| `steps/00-confirmations.md`           | Decisions needed **before** coding                                           | — (human review) |
| `steps/01-models-migrations.md`       | Django models + migrations                                                   | 1                |
| `steps/02-schedule-to-chat.md`        | `git mv apps/schedule apps/chat` + wiring                                    | 1                |
| `steps/03-uffs-api-cache.md`          | Download + cache UFFS schedule API data                                      | 1                |
| `steps/04-extract-exams-migration.md` | Move `get_exam_json.py` → `rag_ingestion` management command + async service | 1                |
| `steps/05-upload-wizard.md`           | 3-step mobile upload wizard (views + templates + JS)                         | 2–3              |
| `steps/06-chat-interface.md`          | Web chat UI: sidebar, chat view, RAG integration                             | 2                |
| `steps/07-frontend-design.md`         | Design tokens, shared CSS/components, responsive polish                      | 1                |

---

## Dependency Graph

```
00-confirmations
      │
      ├─► 01-models-migrations ──────────────────────┐
      │         │                                     │
      │         ├─► 04-extract-exams-migration        │
      │         │         │                           │
      │         │         └─► 05-upload-wizard ───────┤
      │         │                                     │
      │         └─► 03-uffs-api-cache ──────────────► 06-chat-interface
      │                                               │
      └─► 02-schedule-to-chat ────────────────────────┘
                                                      │
                                             07-frontend-design
                                          (runs after 05 + 06 drafts exist)
```

---

## Cross-Cutting Rules for All Agents

- Run `uv run ruff check .` before marking a step complete.
- Run `uv run python manage.py test` after any model or view change.
- After any model change, run `uv run python manage.py makemigrations` and **paste the generated file** in the output — do not hand-write migrations.
- Never delete or hand-edit existing migration files.
- Use `HTMX` for form interactions and partial page updates (add `django-htmx` to `pyproject.toml`).
- Mobile-first CSS; all templates extend a shared `base.html` (to be created in step 07).
- Use `djlint` formatting for all templates.
- No need for backwards compatibility anywhere in this project (not in production) — when a step replaces a file or script, delete the old one outright instead of deprecating it.
