# Multi-stage build for auth service
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy auth service requirements
COPY auth_service/requirements.txt ./auth_service_requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r auth_service_requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (check if user exists first)
RUN (useradd -m -u 1000 netra 2>/dev/null || true) && \
    mkdir -p /app/logs && \
    chown -R 1000:1000 /app

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy auth service code
COPY --chown=netra:netra auth_service/ ./auth_service/
COPY --chown=netra:netra shared/ ./shared/
COPY --chown=netra:netra test_framework/ ./test_framework/

# Switch to non-root user
USER netra

# Environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

# Expose auth service port
EXPOSE 8081

# Default command for auth service
CMD ["uvicorn", "auth_service.main:app", "--host", "0.0.0.0", "--port", "8081", "--reload", "--reload-dir", "/app/auth_service"]