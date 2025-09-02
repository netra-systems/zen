# Minimal Pytest Collection Dockerfile
# Optimized for test discovery and collection only
# Prevents OOM during test collection phase

# Multi-stage build for minimal final size
FROM python:3.11-slim as base

# Set memory-efficient environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONHASHSEED=random
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Create working directory
WORKDIR /app

# Install only essential system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# --- Dependencies Stage ---
FROM base as deps

# Copy only requirements files for better layer caching
COPY requirements.txt /app/
COPY test_framework/requirements.txt /app/test_framework/

# Create minimal requirements file for collection
RUN cat > /app/collection_requirements.txt << 'EOF'
# Minimal requirements for pytest collection only
pytest>=8.4.1
pytest-asyncio>=1.1.0
pydantic>=2.11.7
fastapi>=0.116.1
sqlalchemy>=2.0.43
sqlmodel>=0.0.24
python-dotenv>=1.1.1
beartype>=0.21.0
EOF

# Install only collection dependencies
RUN pip install --no-cache-dir -r /app/collection_requirements.txt

# --- Final Stage ---
FROM base as final

# Copy installed packages from deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy only test files and minimal application structure
COPY tests/ /app/tests/
COPY netra_backend/__init__.py /app/netra_backend/
COPY netra_backend/app/__init__.py /app/netra_backend/app/
COPY netra_backend/models/__init__.py /app/netra_backend/models/
COPY shared/__init__.py /app/shared/
COPY test_framework/__init__.py /app/test_framework/

# Create stub files to satisfy imports
RUN mkdir -p /app/netra_backend/app \
    && echo "# Stub file for collection" > /app/netra_backend/app/main.py \
    && echo "# Stub file for collection" > /app/netra_backend/models/base.py

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Create non-root user with minimal permissions
RUN useradd -m -u 1000 -s /bin/sh testuser \
    && chown -R testuser:testuser /app
USER testuser

# Memory limits for container
ENV MALLOC_MMAP_THRESHOLD_=131072
ENV MALLOC_TRIM_THRESHOLD_=131072
ENV MALLOC_TOP_PAD_=131072

# Default command for test collection
CMD ["pytest", "--collect-only", "--quiet", "tests/"]