# /v2/Dockerfile
# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Add any system dependencies here if needed (e.g., for database drivers)
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Copy only the requirements file first to leverage Docker layer caching
COPY ./v2/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY ./v2 /app/v2

# Expose the port the app runs on
EXPOSE 8000

# Run the application using Uvicorn
# This will run the FastAPI app defined in /app/v2/api.py
CMD ["uvicorn", "v2.api:app", "--host", "0.0.0.0", "--port", "8000"]
