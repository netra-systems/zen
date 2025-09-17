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

# Validate critical imports at build time to catch import issues before deployment
RUN python -c "import sys; sys.path.insert(0, '/app'); from netra_backend.app.core.environment_context.cloud_environment_detector import get_cloud_environment_detector, CloudPlatform; print('✅ CloudEnvironmentDetector import validation successful')"

# Set environment variables
ENV PYTHONPATH=/app

# Run the application 
# Cloud Run sets PORT environment variable automatically
# CRITICAL: Using 1 worker for debugging GCP deployment issues
CMD ["sh", "-c", "uvicorn netra_backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --timeout-keep-alive 75 --timeout-graceful-shutdown 30"]
