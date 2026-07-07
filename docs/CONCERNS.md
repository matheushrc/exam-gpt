# Open concerns

Notes from a repo-wide pass, kept here instead of fixed inline because they
either need a decision or are bigger than the current sprint.

## Mobile chat: source details do not scroll into view

Found testing the chat page on a real Android phone (Chrome, 410x770 CSS
viewport). Expanding the "Fontes citadas" `<details>` in a chat answer doesn't
scroll the revealed content into view: `.chat-scroll` stays at `scrollTop: 0`
after expansion, so the newly shown source card renders behind the floating
`.chat-input-area` bar until the user manually scrolls.

## No authentication on any endpoint (deferred — too complex for this sprint)

DRF's default permission is `AllowAny` (`settings/settings.py` sets no
`DEFAULT_PERMISSION_CLASSES`). No view anywhere sets `permission_classes`.

Compounding this: `ChatMessageView` (`apps/chat/views.py`), `search()`
(`apps/rag_search/search.py`), and `extract.py` all fall back to the
server's own `GOOGLE_API_KEY` env var when the client doesn't supply one.
Today that's fine (local-only, single operator). The day this becomes
multi-user or gets exposed beyond localhost, anyone who can reach `/api/`
can spend the operator's Google API quota with zero rate limiting and no
way to attribute usage to a user.

There's a plan to add real users — once that lands, this whole area
(permission classes, per-user API key requirement, rate limiting) needs a
pass. Flagging now so it isn't forgotten, not asking to fix it this sprint.

## seed_exam_jsons wipes ALL chunks even for a partial run

`rebuild_vector_index()` in `apps/rag_ingestion/embed.py` always runs
`Chunks.objects.all().delete()`, then rebuilds turbo_ids only for the
`Questao`s loaded in the current call. `seed_exam_jsons()` passes only
the questoes from the `json_root` it was given. So seeding a single
file or a subdirectory (instead of the full `input/converted_provas`)
deletes the vector-search chunks for every _other_ already-seeded exam,
making them unsearchable until a full reseed. There's also no pruning
of `Prova`/`Questao` rows for JSON files removed from `json_root`
between runs — those rows persist in Mongo even though their chunks get
dropped on the next full reseed.

## seed_exam_jsons aborts the whole batch on one bad file

`seed_exam_jsons()` loops over every JSON file and calls `upsert_exam()`
synchronously before generating any embeddings. If one file doesn't
match the current `Prova`/`Questao` schema (e.g. a stale field name), it
raises immediately and no exam from that run gets written — including
ones already processed earlier in the same loop, since the embeddings
step (and thus the only side-effecting write that matters for search)
never runs. Hit this directly: 12 exam JSONs in `input/converted_provas`
still had the pre-`ano_semestre` `ano`+`semestre` shape from before
commit `36ab523`, so every seed attempt failed with `KeyError:
'ano_semestre'` on the first file with no error surfaced anywhere a user
would see it (the chat just kept returning empty results). Worth either
validating/skipping bad files individually or failing loudly in a way
that's easy to notice.

## mypy is configured but not installed

`pyproject.toml` has a `[tool.mypy]` block with the django-stubs plugin,
and AGENTS.md claims "this project includes Django mypy/stub
configuration" — but `mypy` itself isn't in `[dependency-groups].dev`
(only `django-stubs`, `ipykernel`, `python-dotenv` are). Confirmed:
`uv run mypy apps` fails with "No such file or directory". The stub
config is currently unusable.

## Minor / lower priority

- `apps/rag_search/views.py`: `top_k` query param has no upper bound —
  a client can request an arbitrarily large `top_k`, forcing a large
  vector-index scan and Mongo `IN` query. Cheap DoS vector if ever
  exposed publicly (ties into the auth gap above).
- `settings/settings.py`: `SECRET_KEY` has a checked-in insecure
  fallback and `DEBUG` defaults to `"True"` when unset. Intentional for
  a non-production project, but a footgun if this ever gets deployed
  without both env vars explicitly set.
- `apps/rag_ingestion/models.py`: `Questao`'s `UniqueConstraint` on
  `(ordem, enunciado)` isn't scoped by `materia`/`prova`. Two different
  subjects with a verbatim-identical short question (e.g. a true/false
  statement) at the same `ordem` would collide. Unlikely given how
  specific exam text usually is, but worth knowing about if
  duplicate-question bugs show up.
- `apps/rag_ingestion/embed.py` and `apps/rag_ingestion/seed_exams.py`
  use bare `print()` for progress output instead of `logging`,
  inconsistent with how management commands use `self.stdout.write`.
  Style nit, not a bug.
