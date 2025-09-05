# Podman-optimized Auth Service Dockerfile
FROM python:3.11-alpine3.19

# Install system dependencies in one layer
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    postgresql-dev \
    curl \
    && rm -rf /var/cache/apk/*

# Set working directory
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY auth_service /app/auth_service
COPY shared /app/shared

# Set Python environment
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

EXPOSE 8081

# Run with uvicorn
CMD ["python", "-m", "uvicorn", "auth_service.main:app", "--host", "0.0.0.0", "--port", "8081"]