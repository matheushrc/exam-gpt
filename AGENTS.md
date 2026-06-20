# Repository Guidelines

## Project Structure & Module Organization

This is a Django project for exam ingestion and RAG-style search. The project
configuration lives in `settings/`, with app code under `apps/`. Current apps
include `apps/rag_ingestion/`, `apps/rag_search/`, and `apps/schedule/`. Shared
HTML templates are in `templates/`; app-specific templates may live inside each
app, such as `apps/schedule/templates/`. Mongo migration snapshots are stored in
`mongo_migrations/`. Research notes are numbered in `research/`, product ideas
live in `IDEAS.md`, and sample inputs live in `input/`. Prompt assets live in
`prompts/` and `apps/rag_ingestion/prompts/`.

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

## Coding Style & Naming Conventions

Use Python 3.14+ and Django conventions. Indent Python with 4 spaces, keep module
names lowercase with underscores, and name Django apps, views, models, and
schemas clearly by domain. Prefer typed functions where practical; this project
includes Django mypy/stub configuration. Format templates with DJLint using
4-space indentation. Use Ruff for Python linting before committing.

## Testing Guidelines

Tests currently follow Django's app-local pattern, for example
`apps/rag_search/tests.py` and `apps/rag_ingestion/tests.py`. Add tests near the
app code they exercise, name test methods descriptively, and cover model,
schema, ingestion, and view behavior when changing those areas. Run
`uv run python manage.py test` before opening a pull request.

## Commit & Pull Request Guidelines

Recent history uses concise, imperative commit messages, sometimes with a
conventional prefix such as `feat(scope):`, `fix(scope):`, or `refactor(scope):`.
Keep commits focused, for example `fix(settings): update default mongo host`.

Pull requests should include a short summary, the commands run for verification,
linked issues when applicable, and screenshots or API examples for UI/API
changes. Call out new environment variables, migrations, or data-indexing steps.

## Agent-Specific Instructions

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
