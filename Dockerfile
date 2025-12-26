# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Use uv + uv.lock for reproducible installs
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir uv

# Create writable dirs used by the app
RUN mkdir -p /app/logs

# Install dependencies first (better build cache)
COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen

COPY . /app

EXPOSE 8000

CMD ["uv", "run", "./manage.py", "runserver", "0.0.0.0:8000"]
