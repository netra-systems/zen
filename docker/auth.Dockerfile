# Production Dockerfile for Auth Service
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
COPY auth_service/requirements.txt .
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
COPY --chown=netra:netra auth_service /app/auth_service
COPY --chown=netra:netra shared /app/shared

# Set Python path
ENV PATH=/home/netra/.local/bin:$PATH
ENV PYTHONPATH=/app

# Docker environment indicator
ENV RUNNING_IN_DOCKER=true

# Switch to non-root user
USER netra

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

# Expose port
EXPOSE 8081

# Default command for production
CMD ["sh", "-c", "gunicorn auth_service.main:app -w ${WORKERS:-2} -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8081 --timeout 120 --graceful-timeout 30 --access-logfile - --error-logfile - --log-level ${LOG_LEVEL:-info}"]