# Netra Backend - Staging Deployment
# Optimized for production-like staging validation with request isolation
# CRITICAL: Must match production configuration exactly

FROM python:3.11-slim as base

# System dependencies and security updates
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        curl \
        ca-certificates \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r netra && useradd -r -g netra netra

# Set working directory
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY netra_backend/ ./netra_backend/
COPY shared/ ./shared/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=staging

# Create necessary directories
RUN mkdir -p /app/logs /app/tmp && \
    chown -R netra:netra /app

# Switch to non-root user
USER netra

# Health check for staging validation
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Command to run the application with staging-optimized settings
CMD ["uvicorn", "netra_backend.app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--access-log", \
     "--log-level", "info", \
     "--timeout-keep-alive", "65"]