FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY netra_backend/ ./netra_backend/
COPY shared/ ./shared/
COPY auth_service/ ./auth_service/

# Set environment variables
ENV PYTHONPATH=/app

# Run the application 
# Cloud Run sets PORT environment variable automatically
# CRITICAL: Using 1 worker for debugging GCP deployment issues
CMD ["sh", "-c", "uvicorn netra_backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --timeout-keep-alive 75 --timeout-graceful-shutdown 30"]
