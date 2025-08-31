# Test Data Seeder Dockerfile
# Loads test fixtures into real databases
FROM python:3.11-slim

WORKDIR /app

# Install database clients
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir \
    asyncpg \
    redis \
    clickhouse-driver \
    pydantic \
    pydantic-settings

# Copy seeding scripts
COPY test_framework/fixtures /app/fixtures
COPY scripts/test_seed_data.py /app/seed_data.py

# Create non-root user
RUN useradd -m -u 1000 testuser
USER testuser

CMD ["python", "seed_data.py"]