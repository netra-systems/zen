# Alpine-based Production Dockerfile for Backend Service
# Optimized for test isolation and minimal size
FROM python:3.11-alpine3.19 as builder

# Build arguments
ARG BUILD_ENV=test

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    postgresql-dev \
    make \
    g++ \
    linux-headers

# Set working directory
WORKDIR /build

# Copy and install requirements from root directory
COPY requirements.txt .
RUN pip install --no-cache-dir --user \
    --no-warn-script-location \
    -r requirements.txt

# Production stage - minimal Alpine image
FROM python:3.11-alpine3.19

# Install runtime dependencies only
RUN apk add --no-cache \
    libpq \
    curl \
    tini \
    lz4-libs \
    && rm -rf /var/cache/apk/*

# Create non-root user
RUN addgroup -g 1000 netra && \
    adduser -D -u 1000 -G netra netra && \
    mkdir -p /app/logs /app/data && \
    chown -R netra:netra /app

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder --chown=netra:netra /root/.local /home/netra/.local

# Copy only necessary application code (production build)
COPY --chown=netra:netra netra_backend /app/netra_backend
COPY --chown=netra:netra shared /app/shared
COPY --chown=netra:netra alembic /app/alembic
COPY --chown=netra:netra scripts /app/scripts
COPY --chown=netra:netra SPEC /app/SPEC

# Set environment
ENV PATH=/home/netra/.local/bin:$PATH
ENV PYTHONPATH=/app:$PYTHONPATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV RUNNING_IN_DOCKER=true
ENV BUILD_ENV=${BUILD_ENV}

# Security: Drop all capabilities
USER netra

# Use tini for proper signal handling
ENTRYPOINT ["/sbin/tini", "--"]

# Health check
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Production command with optimized workers
CMD ["sh", "-c", "alembic -c netra_backend/alembic.ini upgrade head && gunicorn netra_backend.app.main:app -w ${WORKERS:-2} -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 60 --graceful-timeout 10 --access-logfile - --error-logfile - --log-level ${LOG_LEVEL:-error}"]