# Auth Service Test Dockerfile
# Optimized for fast test execution with minimal dependencies

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY auth_service/requirements.txt /app/auth_service/
COPY test_framework/requirements.txt /app/test_framework/

# Install Python dependencies
RUN pip install --no-cache-dir -r auth_service/requirements.txt && \
    pip install --no-cache-dir -r test_framework/requirements.txt && \
    pip install --no-cache-dir pytest pytest-asyncio pytest-cov

# Copy application code
COPY auth_service /app/auth_service
COPY shared /app/shared
COPY test_framework /app/test_framework
COPY scripts /app/scripts

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH
ENV PYTHONUNBUFFERED=1

# Create non-root user for security
RUN useradd -m -u 1000 testuser && chown -R testuser:testuser /app
USER testuser

# Health check endpoint
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:8082/health || exit 1

# Default command
CMD ["uvicorn", "auth_service.main:app", "--host", "0.0.0.0", "--port", "8082"]