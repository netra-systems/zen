# Backend Test Dockerfile
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
COPY requirements.txt /app/
COPY test_framework/requirements.txt /app/test_framework/

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt && \
    pip install --no-cache-dir -r test_framework/requirements.txt && \
    pip install --no-cache-dir pytest pytest-asyncio pytest-cov

# Copy application code
COPY netra_backend /app/netra_backend
COPY shared /app/shared
COPY test_framework /app/test_framework
COPY tests /app/tests
COPY scripts /app/scripts
COPY SPEC /app/SPEC

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH
ENV PYTHONUNBUFFERED=1

# Create non-root user for security
RUN useradd -m -u 1000 testuser && chown -R testuser:testuser /app
USER testuser

# Health check endpoint
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

# Default command
CMD ["uvicorn", "netra_backend.app.main:app", "--host", "0.0.0.0", "--port", "8001"]