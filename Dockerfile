FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim

WORKDIR /app

ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1

COPY pyproject.toml uv.lock ./

RUN uv pip install --system -r pyproject.toml

COPY manage.py ./
COPY settings/ ./settings/
COPY apps/ ./apps/
COPY templates/ ./templates/
COPY mongo_migrations/ ./mongo_migrations/

CMD ["sh", "-c", "python manage.py migrate --run-syncdb && python manage.py runserver 0.0.0.0:${PORT}"]
