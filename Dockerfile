# Start with a Python image.
FROM python:3.11 AS fediverser_base

ENV PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  POETRY_VIRTUALENVS_CREATE=false \
  POETRY_CACHE_DIR='/var/cache/pypoetry'

# Copy all relevant files into the image.
COPY ./fediverser /app/fediverser
COPY ./README.md /app
COPY ./pyproject.toml /app
COPY ./pytest.ini /app
COPY ./poetry.lock /app
COPY ./setup.cfg /app/fediverse
WORKDIR /app

RUN apt-get update
RUN apt-get install build-essential cargo -y

# Install poetry
RUN pip install poetry

# Use poetry to install all dependencies
RUN poetry install
