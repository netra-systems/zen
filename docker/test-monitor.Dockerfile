# Test Service Monitor Dockerfile
# Monitors health of test services during testing
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    asyncio \
    aiohttp \
    asyncpg \
    redis \
    clickhouse-driver

# Copy monitoring script
COPY scripts/test_service_monitor.py /app/monitor.py

# Create non-root user
RUN useradd -m -u 1000 testuser
USER testuser

EXPOSE 8080

CMD ["python", "monitor.py"]