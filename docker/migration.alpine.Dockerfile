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
COPY alembic /app/alembic
COPY netra_backend/alembic.ini /app/netra_backend/alembic.ini
COPY netra_backend/app/models /app/netra_backend/app/models
COPY shared/isolated_environment.py /app/shared/isolated_environment.py

# Set environment
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV RUNNING_IN_DOCKER=true
ENV BUILD_ENV=test

# Run migrations and exit
CMD ["sh", "-c", "alembic -c netra_backend/alembic.ini upgrade head && echo 'Migrations completed successfully'"]