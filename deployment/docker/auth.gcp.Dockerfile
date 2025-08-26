FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including tini for proper signal handling
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY auth_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install gunicorn for production deployment
RUN pip install gunicorn

# Copy application code
COPY auth_service/ ./auth_service/
COPY shared/ ./shared/

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Use tini as entrypoint for proper signal handling
ENTRYPOINT ["tini", "-g", "--"]

# Run the application with gunicorn configuration file
CMD ["gunicorn", "auth_service.main:app", "--config", "auth_service/gunicorn_config.py"]