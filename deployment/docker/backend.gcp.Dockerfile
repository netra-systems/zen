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

# Set environment variables
ENV PYTHONPATH=/app

# Run the application 
# Cloud Run sets PORT environment variable automatically
CMD ["sh", "-c", "uvicorn netra_backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
