# syntax=docker/dockerfile:1.4
# Enable BuildKit for advanced caching features
# Multi-stage build optimized for layer caching

FROM python:3.11-slim AS python-base

# Python environment setup
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    PYSETUP_PATH="/opt/pysetup"

# ==============================================================================
# BUILDER-BASE: System dependencies that rarely change
FROM python-base AS builder-base
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR $PYSETUP_PATH

# ==============================================================================
# DEPENDENCY-CORE: Core dependencies that rarely change
FROM builder-base AS dependency-core

# Create requirements layers - split by change frequency
RUN --mount=type=bind,source=requirements.txt,target=/tmp/requirements.txt \
    --mount=type=cache,target=/root/.cache/pip,id=pip-cache-core \
    grep -E "^(fastapi|uvicorn|gunicorn|sqlalchemy|pydantic|redis|asyncpg|psycopg2)" /tmp/requirements.txt > requirements-core.txt && \
    pip install --user -r requirements-core.txt

# ==============================================================================
# DEPENDENCY-APP: Application dependencies that occasionally change  
FROM dependency-core AS dependency-app

RUN --mount=type=bind,source=requirements.txt,target=/tmp/requirements.txt \
    --mount=type=cache,target=/root/.cache/pip,id=pip-cache-app \
    grep -vE "^(fastapi|uvicorn|gunicorn|sqlalchemy|pydantic|redis|asyncpg|psycopg2)" /tmp/requirements.txt > requirements-app.txt && \
    pip install --user -r requirements-app.txt || true

# ==============================================================================
# DEPENDENCY-ALL: Complete dependency installation
FROM dependency-app AS dependency-all

# Final pass to ensure all dependencies including transitive ones
RUN --mount=type=bind,source=requirements.txt,target=/tmp/requirements.txt \
    --mount=type=cache,target=/root/.cache/pip,id=pip-cache-all \
    pip install --user -r /tmp/requirements.txt

# ==============================================================================
# PRODUCTION: Final optimized image
FROM python:3.11-slim AS production

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 netra \
    && mkdir -p /app/logs /app/data \
    && chown -R netra:netra /app

WORKDIR /app

# Copy Python packages from builder (this layer rarely invalidates)
COPY --from=dependency-all --chown=netra:netra /root/.local /home/netra/.local

# Set Python path before copying app code
ENV PATH=/home/netra/.local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

# Copy shared/framework code (changes less frequently than app code)
COPY --chown=netra:netra shared/ ./shared/
COPY --chown=netra:netra test_framework/ ./test_framework/
COPY --chown=netra:netra SPEC/ ./SPEC/

# Copy Alembic migrations (changes occasionally)
COPY --chown=netra:netra alembic/ ./alembic/

# Copy scripts (changes occasionally)  
COPY --chown=netra:netra scripts/ ./scripts/

# Copy application code last (changes most frequently)
COPY --chown=netra:netra netra_backend/ ./netra_backend/

USER netra

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# For development with hot reload
CMD ["uvicorn", "netra_backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/netra_backend"]