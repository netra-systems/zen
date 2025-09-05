# Podman-optimized Dockerfile for backend service
# Focuses on layer caching without BuildKit-specific features

FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Layer 1: Core dependencies (rarely change)
# Create a subset requirements file for core deps
RUN echo "fastapi>=0.116.1" > requirements-core.txt && \
    echo "uvicorn[standard]>=0.35.0" >> requirements-core.txt && \
    echo "gunicorn>=23.0.0" >> requirements-core.txt && \
    echo "sqlalchemy>=2.0.43" >> requirements-core.txt && \
    echo "pydantic>=2.11.7" >> requirements-core.txt && \
    echo "redis>=6.4.0" >> requirements-core.txt && \
    echo "asyncpg>=0.30.0" >> requirements-core.txt && \
    echo "psycopg2-binary>=2.9.10" >> requirements-core.txt && \
    pip install --no-cache-dir --user -r requirements-core.txt

# Layer 2: Full requirements (changes occasionally) 
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 netra \
    && mkdir -p /app/logs /app/data \
    && chown -R netra:netra /app

WORKDIR /app

# Copy Python packages (this layer rarely changes)
COPY --from=builder --chown=netra:netra /root/.local /home/netra/.local

# Environment setup
ENV PATH=/home/netra/.local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

# Copy static/config files (change infrequently)
COPY --chown=netra:netra SPEC/ ./SPEC/
COPY --chown=netra:netra alembic/ ./alembic/

# Copy shared libraries (change occasionally)
COPY --chown=netra:netra shared/ ./shared/
COPY --chown=netra:netra test_framework/ ./test_framework/

# Copy scripts (change occasionally)
COPY --chown=netra:netra scripts/ ./scripts/

# Copy application code last (changes frequently)
COPY --chown=netra:netra netra_backend/ ./netra_backend/

USER netra

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "netra_backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/netra_backend"]