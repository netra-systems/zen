# Netra Database Migrations - Alpine-Optimized Container
# Purpose: Run Alembic database migrations as a separate Cloud Run Job
# This container is NOT for running the application, only for migrations

FROM python:3.11-alpine3.19

# Install build dependencies needed for database drivers
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    libpq \
    && rm -rf /var/cache/apk/*

WORKDIR /app

# Copy only what's needed for migrations
COPY requirements.txt .

# Install minimal dependencies for migrations
# We only need: alembic, sqlalchemy, psycopg2, and their dependencies
RUN pip install --no-cache-dir \
    alembic \
    sqlalchemy \
    psycopg2-binary \
    python-dotenv

# Copy migration files and configuration
COPY netra_backend/app/alembic /app/alembic
COPY shared/isolated_environment.py /app/shared/isolated_environment.py
COPY shared/__init__.py /app/shared/__init__.py

# Create a proper alembic.ini that points to the correct location
RUN cat > alembic.ini << 'EOF'
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = postgresql://%(POSTGRES_USER)s:%(POSTGRES_PASSWORD)s@%(POSTGRES_HOST)s:%(POSTGRES_PORT)s/%(POSTGRES_DB)s

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
EOF

# Set Python path
ENV PYTHONPATH=/app

# Default command runs migrations
# Can be overridden to run specific migration commands
CMD ["alembic", "upgrade", "head"]