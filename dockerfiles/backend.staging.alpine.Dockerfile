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

# Explicitly ensure monitoring module is included (Fix for staging outage - Issue #1278)
COPY netra_backend/app/services/monitoring/ ./netra_backend/app/services/monitoring/

# CloudEnvironmentDetector import validation (Issue #1305)
RUN python -c "from netra_backend.app.core.environment_context.cloud_environment_detector import CloudEnvironmentDetector; print('✅ CloudEnvironmentDetector import validation successful')" || (echo "❌ CloudEnvironmentDetector import failed" && exit 1)

# Set environment variables
ENV PYTHONPATH=/app

# Run the application with gunicorn+uvicorn for Cloud Run stability
CMD ["sh", "-c", "gunicorn netra_backend.app.main:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} --timeout 300 --access-logfile - --error-logfile -"]
