# Backend Test Dockerfile - Memory Optimized
# Prevents OOM crashes with advanced memory management and layer optimization

# Multi-stage build for optimal layer caching
FROM python:3.11-slim as base

# Memory-optimized environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONHASHSEED=random
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Memory management settings to prevent OOM
ENV MALLOC_MMAP_THRESHOLD_=131072
ENV MALLOC_TRIM_THRESHOLD_=131072
ENV MALLOC_TOP_PAD_=131072
ENV MALLOC_ARENA_MAX=2

# Set working directory
WORKDIR /app

# --- System Dependencies Stage ---
FROM base as system

# Install minimal system dependencies with cleanup
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && find /var/lib/apt -type f -delete

# --- Dependencies Stage ---  
FROM system as deps

# Copy requirements for optimal layer caching
COPY requirements.txt /app/
COPY test_framework/requirements.txt /app/test_framework/

# Install ALL dependencies from main requirements to ensure nothing is missing
# This ensures the test environment matches production
RUN pip install --no-cache-dir --compile -r /app/requirements.txt \
    && pip install --no-cache-dir --compile -r /app/test_framework/requirements.txt \
    && python -m compileall /usr/local/lib/python3.11/site-packages \
    && find /usr/local/lib/python3.11/site-packages -name "*.pyc" -delete \
    && find /usr/local/lib/python3.11/site-packages -name "__pycache__" -type d -exec rm -rf {} + \
    && pip list --format=freeze > /app/installed_packages.txt

# --- Application Stage ---
FROM system as app

# Copy optimized dependencies from deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin
COPY --from=deps /app/installed_packages.txt /app/

# Copy application code selectively
COPY netra_backend/ /app/netra_backend/
COPY shared/ /app/shared/
COPY test_framework/ /app/test_framework/
COPY tests/ /app/tests/
COPY scripts/ /app/scripts/

# Create optimized pytest configuration
RUN cat > /app/pytest.ini << 'EOF'
[tool:pytest]
minversion = 8.0
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --tb=short
    --strict-markers
    --disable-warnings
    --maxfail=5
    --durations=5
markers =
    slow: marks tests as slow
    integration: marks tests as integration
    unit: marks tests as unit tests
asyncio_mode = auto
EOF

# Set Python path and memory limits
ENV PYTHONPATH=/app:$PYTHONPATH

# Create cache and results directories
RUN mkdir -p /app/.pytest_cache /app/test-results \
    && chmod 755 /app/.pytest_cache /app/test-results

# Create non-root user with optimized settings
RUN useradd -m -u 1000 -s /bin/sh testuser \
    && chown -R testuser:testuser /app
USER testuser

# Memory-aware health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=2 \
    CMD python -c "import sys; import psutil; mem=psutil.virtual_memory(); print(f'Memory: {mem.percent}%'); sys.exit(1 if mem.percent > 90 else 0)" || \
        curl -f http://localhost:8001/health || exit 1

# Default command with memory optimization
CMD ["uvicorn", "netra_backend.app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1", "--limit-max-requests", "1000"]