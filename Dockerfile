# Start with a Python image.
FROM python:3.12-slim-bookworm AS fediverser_base

# Install poetry
RUN pip install poetry

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR='/var/cache/pypoetry'

RUN apt-get update
RUN apt-get install build-essential cargo -y

WORKDIR /app
COPY ./pyproject.toml /app
COPY ./poetry.lock /app

RUN poetry install --without dev --no-root && rm -rf $POETRY_CACHE_DIR

# Copy all relevant files into the image.
COPY ./fediverser /app/fediverser
COPY ./pytest.ini /app
COPY ./README.md /app
COPY ./setup.cfg /app/fediverse

FROM fediverser_base AS release
RUN poetry install --without dev

FROM fediverser_base AS development
RUN poetry install
