# Load Testing Container for Staging Validation
# Simulates 100+ concurrent users to validate request isolation

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install load testing tools
RUN pip install --no-cache-dir \
    locust==2.15.1 \
    requests==2.31.0 \
    websockets==11.0.3 \
    asyncio \
    aiohttp \
    pytest \
    psutil

# Copy load testing scripts
COPY scripts/load_testing/ ./scripts/
COPY tests/load/ ./tests/

# Create results directory
RUN mkdir -p /app/results

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default configuration
ENV TARGET_URL=http://backend:8000
ENV MAX_USERS=150
ENV SPAWN_RATE=10
ENV RUN_TIME=3600

# Health check
HEALTHCHECK --interval=60s --timeout=30s --retries=3 \
    CMD python -c "import requests; requests.get('$TARGET_URL/health')" || exit 1

# Entry point script
COPY scripts/load_testing/run_load_test.py ./
CMD ["python", "run_load_test.py"]