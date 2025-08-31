FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including tini for proper signal handling
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY analytics_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install gunicorn for production deployment
RUN pip install gunicorn

# Copy application code
COPY analytics_service/ ./analytics_service/
COPY shared/ ./shared/

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Use tini as entrypoint for proper signal handling
ENTRYPOINT ["tini", "-g", "--"]

# Run the application with gunicorn
CMD ["gunicorn", "analytics_service.main:app", "--bind", "0.0.0.0:8090", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker"]