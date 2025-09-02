# Optimized Pytest Execution Dockerfile
# Memory-efficient test execution with advanced caching
# Prevents OOM during test runs

# Multi-stage build for optimal caching and size
FROM python:3.11-slim as base

# Memory-optimized environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONHASHSEED=random
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

# Memory management settings
ENV MALLOC_MMAP_THRESHOLD_=131072
ENV MALLOC_TRIM_THRESHOLD_=131072
ENV MALLOC_TOP_PAD_=131072
ENV MALLOC_ARENA_MAX=2

WORKDIR /app

# --- System Dependencies Stage ---
FROM base as system

# Install system dependencies with minimal footprint
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && find /var/lib/apt -type f -delete

# --- Dependencies Stage ---
FROM system as deps

# Copy requirements for layer caching
COPY requirements.txt /app/
COPY test_framework/requirements.txt /app/test_framework/

# Create optimized requirements for execution
RUN cat > /app/execution_requirements.txt << 'EOF'
# Core testing framework
pytest>=8.4.1
pytest-asyncio>=1.1.0
pytest-cov>=6.0.0
pytest-xdist>=3.6.0

# Application core (minimal set)
fastapi>=0.116.1
starlette>=0.47.3
uvicorn[standard]>=0.35.0
pydantic>=2.11.7

# Database essentials
sqlalchemy>=2.0.43
sqlmodel>=0.0.24
asyncpg>=0.30.0

# Configuration
python-dotenv>=1.1.1

# Security (minimal)
PyJWT[cryptography]>=2.10.1
bcrypt>=4.3.0

# HTTP client for tests
httpx>=0.28.1

# Utilities
tenacity>=9.1.2
beartype>=0.21.0
python-dateutil>=2.9.0.post0

# Monitoring
psutil>=7.0.0
EOF

# Install execution dependencies with optimizations
RUN pip install --no-cache-dir --compile -r /app/execution_requirements.txt \
    && python -m compileall /usr/local/lib/python3.11/site-packages \
    && find /usr/local/lib/python3.11/site-packages -name "*.pyc" -delete \
    && find /usr/local/lib/python3.11/site-packages -name "__pycache__" -type d -exec rm -rf {} +

# --- Application Stage ---
FROM system as app

# Copy optimized dependencies
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application code with selective copying
COPY netra_backend/ /app/netra_backend/
COPY shared/ /app/shared/
COPY test_framework/ /app/test_framework/
COPY tests/ /app/tests/
COPY conftest.py /app/ 2>/dev/null || true

# Create pytest configuration for optimized execution
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
    --no-header
    --maxfail=3
    --durations=10
markers =
    slow: marks tests as slow
    integration: marks tests as integration
    unit: marks tests as unit tests
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
EOF

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Create cache directories with proper permissions
RUN mkdir -p /app/.pytest_cache /app/test-results \
    && chmod 755 /app/.pytest_cache /app/test-results

# Create non-root user
RUN useradd -m -u 1000 -s /bin/sh testuser \
    && chown -R testuser:testuser /app
USER testuser

# Health check for test readiness
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=2 \
    CMD python -c "import pytest; import netra_backend" || exit 1

# Default command with memory optimization
CMD ["pytest", "-v", "--tb=short", "--maxfail=5", "--disable-warnings", "tests/"]