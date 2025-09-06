# Alpine-based Production Dockerfile for Backend Service
# Optimized for fast builds with aggressive layer caching
FROM python:3.11-alpine3.19 as builder

# Build arguments
ARG BUILD_ENV=test

# Install build dependencies in single layer for caching
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    postgresql-dev \
    make \
    g++ \
    linux-headers \
    rust \
    cargo \
    && rm -rf /var/cache/apk/*

# Set working directory
WORKDIR /build

# CRITICAL: Copy requirements.txt FIRST for optimal layer caching
# This layer only rebuilds when requirements change, not on code changes
COPY requirements.txt .

# Install requirements with cache mount for maximum speed
# Use BuildKit cache mount to persist pip cache across builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user \
    --no-warn-script-location \
    --disable-pip-version-check \
    -r requirements.txt || \
    pip install --no-cache-dir --user \
    --no-warn-script-location \
    --disable-pip-version-check \
    -r requirements.txt

# Production stage - minimal Alpine image
FROM python:3.11-alpine3.19

# Build arguments passed to runtime
ARG BUILD_ENV=test

# Install runtime dependencies only - combine in single layer
RUN apk add --no-cache \
    libpq \
    curl \
    tini \
    lz4-libs \
    libgcc \
    libstdc++ \
    && rm -rf /var/cache/apk/*

# Create non-root user and directories in single layer
RUN addgroup -g 1000 netra && \
    adduser -D -u 1000 -G netra netra && \
    mkdir -p /app/logs /app/data /app/temp && \
    chown -R netra:netra /app

WORKDIR /app

# Copy pre-built Python packages from builder stage
# This is the expensive layer that rarely changes
COPY --from=builder --chown=netra:netra /root/.local /home/netra/.local

# Copy configuration and migration files (changes less frequently)
COPY --chown=netra:netra alembic /app/alembic
COPY --chown=netra:netra SPEC /app/SPEC

# Copy shared libraries (changes moderately)
COPY --chown=netra:netra shared /app/shared

# Copy essential scripts (changes moderately)
# Create scripts directory and copy only essential files 
RUN mkdir -p /app/scripts && touch /app/scripts/__init__.py && chown -R netra:netra /app/scripts
COPY --chown=netra:netra scripts/wait_for_db.py /app/scripts/

# Copy application code LAST (changes most frequently)
# This ensures maximum cache hit rate for builds
COPY --chown=netra:netra netra_backend /app/netra_backend

# Set environment variables
ENV PATH=/home/netra/.local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RUNNING_IN_DOCKER=true \
    BUILD_ENV=test \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random

# Security: Drop all capabilities
USER netra

# Use tini for proper signal handling
ENTRYPOINT ["/sbin/tini", "--"]

# Health check with shorter intervals for faster startup detection
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Optimized startup command with database migration
CMD ["sh", "-c", "\
    echo 'Starting backend service...' && \
    python scripts/wait_for_db.py --max-attempts 30 --delay 2 && \
    echo 'Running database migrations...' && \
    alembic -c netra_backend/alembic.ini upgrade head && \
    echo 'Starting Gunicorn server...' && \
    exec gunicorn netra_backend.app.main:app \
        -w ${WORKERS:-2} \
        -k uvicorn.workers.UvicornWorker \
        --bind 0.0.0.0:8000 \
        --timeout ${TIMEOUT:-60} \
        --graceful-timeout 10 \
        --keep-alive 5 \
        --max-requests 1000 \
        --max-requests-jitter 100 \
        --access-logfile - \
        --error-logfile - \
        --log-level ${LOG_LEVEL:-error} \
        --worker-tmp-dir /dev/shm"]