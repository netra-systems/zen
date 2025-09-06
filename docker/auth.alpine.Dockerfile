# Alpine-based Production Dockerfile for Auth Service
# Optimized for test isolation and minimal size
FROM python:3.11-alpine3.19 AS builder

# Build arguments
ARG BUILD_ENV=test

# Install minimal build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    postgresql-dev

# Set working directory
WORKDIR /build

# Copy and install requirements
COPY auth_service/requirements.txt .
RUN pip install --no-cache-dir --user \
    --no-warn-script-location \
    -r requirements.txt

# Production stage - minimal Alpine image
FROM python:3.11-alpine3.19

# Install minimal runtime dependencies
RUN apk add --no-cache \
    libpq \
    curl \
    tini \
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
COPY --chown=netra:netra auth_service /app/auth_service
COPY --chown=netra:netra shared /app/shared

# Set environment
ENV PATH=/home/netra/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV RUNNING_IN_DOCKER=true
ENV BUILD_ENV=test

# Security: Drop all capabilities
USER netra

# Use tini for proper signal handling
ENTRYPOINT ["/sbin/tini", "--"]

# Health check
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

EXPOSE 8081

# Production command with optimized settings
CMD ["sh", "-c", "python -m auth_service.main"]