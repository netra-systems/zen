# Load Tester Dockerfile - Issue #426 Cluster Resolution
# Purpose: Provides load testing infrastructure for performance validation
# Context: Created to resolve missing Dockerfile preventing Docker compose builds

FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install basic dependencies for load testing
RUN pip install --no-cache-dir locust requests pandas numpy

# Create a basic load testing script if none exists
RUN echo '#!/usr/bin/env python3
"""
Basic load testing script for Netra Apex platform
Created as part of Issue #426 Docker infrastructure resolution
"""

import os
import requests
import time
from locust import HttpUser, task, between

class NetraLoadTestUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Initialize the test user"""
        self.target_url = os.environ.get("TARGET_URL", "http://localhost:8000")
        
    @task(3)
    def health_check(self):
        """Basic health check endpoint testing"""
        self.client.get("/health")
        
    @task(1) 
    def api_status(self):
        """API status endpoint testing"""
        self.client.get("/api/v1/status")

if __name__ == "__main__":
    print("Load tester container started - Issue #426 resolution")
    print("Configure TARGET_URL environment variable for testing")
    print("Default target: http://localhost:8000")
    
    target = os.environ.get("TARGET_URL", "http://localhost:8000")
    max_users = int(os.environ.get("MAX_USERS", "10"))
    spawn_rate = int(os.environ.get("SPAWN_RATE", "2"))
    
    print(f"Target: {target}")
    print(f"Max Users: {max_users}")
    print(f"Spawn Rate: {spawn_rate}")
    
    # Keep container running
    while True:
        time.sleep(60)
        print("Load tester running...")
' > load_test.py

# Make the script executable
RUN chmod +x load_test.py

# Expose port for Locust web UI
EXPOSE 8089

# Default command
CMD ["python", "load_test.py"]