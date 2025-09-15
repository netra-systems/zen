# Alpine-based Migration Service Dockerfile
# Dedicated service for running database migrations
FROM python:3.11-alpine3.19

# Build arguments
ARG BUILD_ENV=test

# Install minimal dependencies for migrations
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    postgresql-dev \
    && rm -rf /var/cache/apk/*

WORKDIR /app

# Copy only migration-related requirements
COPY requirements-migration.txt .
RUN pip install --no-cache-dir \
    --no-warn-script-location \
    --disable-pip-version-check \
    -r requirements-migration.txt

# Install runtime dependencies
RUN apk del gcc musl-dev && \
    apk add --no-cache libpq && \
    rm -rf /var/cache/apk/*

# Copy migration files and minimal code needed
# CRITICAL: Use correct path structure to match alembic.ini expectations
COPY netra_backend/app/alembic /app/netra_backend/app/alembic
COPY netra_backend/alembic.ini /app/netra_backend/alembic.ini

# Copy all necessary shared modules for DatabaseURLBuilder and environment handling
COPY shared/ /app/shared/

# Copy ALL necessary backend app modules required by migrations
COPY netra_backend/app/ /app/netra_backend/app/

# Create empty __init__.py files to make directories proper Python packages
RUN touch /app/__init__.py && \
    touch /app/netra_backend/__init__.py && \
    touch /app/netra_backend/app/__init__.py && \
    touch /app/shared/__init__.py

# Set environment
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV RUNNING_IN_DOCKER=true
ENV BUILD_ENV=test

# Run migrations with proper error handling for staging deployment
CMD ["sh", "-c", "set -e; echo 'Starting migration job...'; python -c 'from shared.isolated_environment import get_env; print(f\"Environment: {get_env().get(\"ENVIRONMENT\", \"unknown\")}\"'); python -m alembic -c netra_backend/alembic.ini current; python -m alembic -c netra_backend/alembic.ini upgrade head && echo 'Migrations completed successfully'"]