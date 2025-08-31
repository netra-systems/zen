# Production Dockerfile for Backend Service
FROM python:3.11-slim as builder

# Build arguments
ARG BUILD_ENV=production

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 netra && \
    mkdir -p /app/logs && \
    chown -R netra:netra /app

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder --chown=netra:netra /root/.local /home/netra/.local

# Copy application code
COPY --chown=netra:netra netra_backend /app/netra_backend
COPY --chown=netra:netra shared /app/shared
COPY --chown=netra:netra scripts /app/scripts
COPY --chown=netra:netra alembic /app/alembic
COPY --chown=netra:netra SPEC /app/SPEC

# Set Python path
ENV PATH=/home/netra/.local/bin:$PATH
ENV PYTHONPATH=/app:$PYTHONPATH

# Disable Python color output for Cloud Run logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NO_COLOR=1
ENV FORCE_COLOR=0
ENV PY_COLORS=0

# Docker environment indicator
ENV RUNNING_IN_DOCKER=true

# Switch to non-root user
USER netra

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command for production
CMD ["sh", "-c", "alembic -c netra_backend/alembic.ini upgrade head && gunicorn netra_backend.app.main:app -w ${WORKERS:-4} -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120 --graceful-timeout 30 --access-logfile - --error-logfile - --log-level ${LOG_LEVEL:-info}"]