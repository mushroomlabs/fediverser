# Start with a Python image.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS fediverser_base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    UV_PROJECT_ENVIRONMENT="/opt/fediverser/.venv" \
    PATH="/opt/fediverser/.venv/bin:$PATH"

WORKDIR /app
COPY ./pyproject.toml /app
COPY ./uv.lock /app
COPY ./README.md /app
COPY ./fediverser /app/fediverser

FROM fediverser_base AS release

RUN uv sync --frozen

FROM fediverser_base AS development

RUN uv sync --frozen --extra dev
