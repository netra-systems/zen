# Multi-stage build for optimized image size
FROM python:3.11-slim AS builder

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

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

# Copy application code
COPY --chown=netra:netra netra_backend/ ./netra_backend/
COPY --chown=netra:netra shared/ ./shared/
# test_framework is excluded in .dockerignore for production builds
# It's not needed in production containers - only for testing
# CRITICAL: Never copy entire scripts/ folder - see SPEC/learnings/docker_scripts_prohibition_critical.xml
COPY --chown=netra:netra SPEC/ ./SPEC/
# Copy Python files if they exist
# Removed problematic COPY command that uses shell redirection

# Switch to non-root user
USER netra

# Environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command for development (with hot reload)
CMD ["uvicorn", "netra_backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/netra_backend"]