# Repository Guidelines

## Project Structure & Module Organization

This is a Django project for exam ingestion and RAG-style search. The project
configuration lives in `settings/`, with app code under `apps/`. Current apps
include `apps/rag_ingestion/`, `apps/rag_search/`, and `apps/schedule/`. Shared
HTML templates are in `templates/`; app-specific templates may live inside each
app, such as `apps/schedule/templates/`. Mongo migration snapshots are stored in
`mongo_migrations/`. Research notes are numbered in `research/`, product ideas
live in `IDEAS.md`, and sample inputs live in `input/`. Prompt assets live as
Python modules near their agents, such as `apps/rag_ingestion/prompts/` and
`apps/chat/prompts/`.

## Build, Test, and Development Commands

- `uv sync`: install dependencies from `pyproject.toml` and `uv.lock`.
- `uv run python manage.py runserver`: run the Django app locally.
- `uv run python manage.py test`: run all Django tests.
- `uv run python manage.py makemigrations`: create Django model migrations.
- `uv run python manage.py migrate`: apply migrations.
- `docker compose up --build`: run the app and MongoDB together.
- `uv run ruff check .`: lint Python code.
- `uv run djlint templates apps --check`: check Django template formatting.

When asked to deploy and test the application, use Docker Compose instead of the
local Django runserver so MongoDB is available with the app.

Local execution expects environment variables such as `SECRET_KEY`,
`GOOGLE_API_KEY`, `HORARIO_ENDPOINT`, `GROUPS_ENDPOINT`, and Mongo settings when
not using the defaults in `docker-compose.yml`.

## Operational Commands

Use only the commands needed for the task at hand:

- `uv sync`: install dependencies.
- `cp .env.example .env`: create a local env file, then fill `SECRET_KEY`,
  `GOOGLE_API_KEY`, `PORT`, and Mongo settings as needed.
- `docker compose up --build`: run the app with MongoDB.
- `docker compose up mongo`: run only MongoDB for local Django commands.
- `uv run python manage.py migrate`: apply migrations.
- `uv run python manage.py extract_exams`: batch-extract exam material (photo folders or PDFs of any kind --
  text-based or scanned) from `input/provas` into JSON files in `input/converted_provas`.
  Options: `--model gemini-3.5-flash` (default), `--concurrency 2`.
- `GOOGLE_API_KEY="your-google-api-key" uv run python apps/rag_ingestion/seed_exams.py`: seed converted exams and rebuild `indexes/index.tvim`.
- `uv run python manage.py runserver`: run Django locally when MongoDB is already available.
- `uv run python manage.py test`: run tests.
- `uv run python manage.py sync_schedule`: Download and cache UFFS schedule data locally. Run once per semester or when throttled.
- `uv run ruff check .`: lint Python.
- `uv run djlint templates apps --check`: check template formatting.

The generated Turbovec vector index is `indexes/index.tvim`; Mongo stores the
`Chunks.turbo_id` mapping.

## Coding Style & Naming Conventions

Use Python 3.14+ and Django conventions. Indent Python with 4 spaces, keep module
names lowercase with underscores, and name Django apps, views, models, and
schemas clearly by domain. Prefer typed functions where practical; this project
includes Django mypy/stub configuration. Format templates with DJLint using
4-space indentation. Use Ruff for Python linting before committing.

Never run `ruff format`/`ruff check` against migration folders (`*/migrations/*`,
`mongo_migrations/*`) — `pyproject.toml` excludes them via `[tool.ruff]
extend-exclude`, but double-check before running Ruff with a custom path or
config override. Django/Mongo migration files must stay byte-stable except for
legitimate migration-generation diffs.

## Testing Guidelines

Tests currently follow Django's app-local pattern, for example
`apps/rag_search/tests.py` and `apps/rag_ingestion/tests.py`. Add tests near the
app code they exercise, name test methods descriptively, and cover model,
schema, ingestion, and view behavior when changing those areas. Run
`uv run python manage.py test` before opening a pull request.

Verify every change against the running app (Docker Compose), not just unit
tests. Be economical only around exam seeding/extraction (`extract_exams`,
`seed_exam_jsons`) since those burn real Google API quota — reuse already
converted/seeded exams instead of re-running extraction or seeding when not
needed for the change. Chatting through the chat endpoint/UI has no such
cost: always exercise it for real against a running server instead of writing
mocked-response tests for chat behavior.

## Commit & Pull Request Guidelines

Recent history uses concise, imperative commit messages, sometimes with a
conventional prefix such as `feat(scope):`, `fix(scope):`, or `refactor(scope):`.
Keep commits focused, for example `fix(settings): update default mongo host`.

Pull requests should include a short summary, the commands run for verification,
linked issues when applicable, and screenshots or API examples for UI/API
changes. Call out new environment variables, migrations, or data-indexing steps.

## Agent-Specific Instructions

This project is not in production. Changes do not need to be backward
compatible unless the user explicitly asks for compatibility. Prefer the clean
current design over compatibility wrappers, deprecated aliases, or migration
contortions for old local data.

Do not overwrite generated data, migrations, or prompt files without checking
their current purpose. Keep changes scoped to the relevant Django app unless a
cross-project setting or dependency update is required.

For Django model changes, do not hand-write migration files. Update the models
first, then run `uv run python manage.py makemigrations` and inspect the
generated migration before testing.

After implementing code changes, run the relevant tests and checks before
reporting the work as complete. For API or Docker-dependent changes, verify the
behavior through Docker Compose and an actual request such as `curl` when
practical.

When a concern in `CONCERNS.md` gets resolved, delete that entry instead of
marking it "RESOLVED" or leaving a note about the fix — the git history
already has that. Keeping resolved entries around just makes the file grow
unboundedly, which costs tokens every time it's read.
