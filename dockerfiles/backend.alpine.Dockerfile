# Alpine-based Production Dockerfile for Backend Service
# Optimized for fast builds with aggressive layer caching
FROM python:3.11-alpine3.19 as builder

# Build arguments
ARG BUILD_ENV=test

# Install only essential build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    postgresql-dev \
    lz4-dev \
    && rm -rf /var/cache/apk/*

# Set working directory
WORKDIR /build

# CRITICAL: Copy requirements.txt FIRST for optimal layer caching
# This layer only rebuilds when requirements change, not on code changes
COPY requirements.txt .

# Install Python dependencies efficiently
RUN pip install --no-cache-dir --user \
    --no-warn-script-location \
    --disable-pip-version-check \
    -r requirements.txt && \
    find /root/.local -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true && \
    find /root/.local -type d -name 'tests' -exec rm -rf {} + 2>/dev/null || true && \
    find /root/.local -type d -name 'test' -exec rm -rf {} + 2>/dev/null || true

# Production stage - minimal Alpine image
FROM python:3.11-alpine3.19

# Build arguments passed to runtime
ARG BUILD_ENV=test

# Install minimal runtime dependencies
RUN apk add --no-cache \
    libpq \
    curl \
    tini \
    lz4-libs \
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

# Note: Migrations handled by separate migration service
# SPEC folder not needed in runtime container

# Copy shared libraries (changes moderately)
COPY --chown=netra:netra shared /app/shared

# Scripts not needed - handled by application code

# Copy application code LAST (changes most frequently)
# This ensures maximum cache hit rate for builds
COPY --chown=netra:netra netra_backend /app/netra_backend

# Clean up unnecessary files from application
RUN find /app -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true && \
    find /app -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true && \
    find /app -type f -name '*.pyc' -delete && \
    find /app -type f -name '*.pyo' -delete && \
    find /app -type f -name '*.md' -delete && \
    rm -rf /app/netra_backend/tests /app/netra_backend/test_* /app/netra_backend/reports /app/netra_backend/SPEC 2>/dev/null || true

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

# Start Gunicorn directly (migrations handled by separate service)
CMD ["sh", "-c", "\
    echo 'Starting backend service...' && \
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