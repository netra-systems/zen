FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY auth_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY auth_service/ ./auth_service/
COPY shared/ ./shared/

# Set environment variables
ENV PYTHONPATH=/app

# Run the application with gunicorn+uvicorn for Cloud Run stability
CMD ["sh", "-c", "gunicorn auth_service.main:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8001} --timeout 300 --access-logfile - --error-logfile -"]
