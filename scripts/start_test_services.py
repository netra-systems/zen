#!/usr/bin/env python
"""
Start test services for frontend real service testing.

This script manages Docker containers and local services needed for
running frontend tests against real backend services.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared.isolated_environment import get_env


def check_docker_running():
    """Check if Docker is running."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0
    except FileNotFoundError:
        print("Docker is not installed")
        return False


def start_docker_services():
    """Start Docker services using docker-compose."""
    compose_file = PROJECT_ROOT / "docker-compose.alpine-test.yml"
    
    if not compose_file.exists():
        # Create a basic test compose file
        create_test_compose_file(compose_file)
    
    print("Starting Docker services...")
    cmd = [
        "docker-compose",
        "-f", str(compose_file),
        "-p", "netra-test",
        "up", "-d"
    ]
    
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print("Failed to start Docker services")
        return False
    
    print("Docker services started successfully")
    return True


def create_test_compose_file(compose_file):
    """Create a basic docker-compose.alpine-test.yml file."""
    content = """version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: netra_test
      POSTGRES_PASSWORD: test_password
      POSTGRES_DB: netra_test
    ports:
      - "5433:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U netra_test"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6380:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
"""
    
    print(f"Creating {compose_file}...")
    compose_file.write_text(content)


def start_local_services():
    """Start local backend services."""
    print("Starting local backend services...")
    
    # Start backend
    backend_process = subprocess.Popen(
        [sys.executable, "scripts/dev_launcher.py", "--service", "backend"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Start auth service
    auth_process = subprocess.Popen(
        [sys.executable, "scripts/dev_launcher.py", "--service", "auth"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    print("Waiting for services to be ready...")
    time.sleep(5)
    
    # Check if services are running
    if not check_service_health("http://localhost:8000/health"):
        print("Backend service failed to start")
        backend_process.terminate()
        auth_process.terminate()
        return False
    
    if not check_service_health("http://localhost:8081/health"):
        print("Auth service failed to start")
        backend_process.terminate()
        auth_process.terminate()
        return False
    
    print("Local services started successfully")
    return True


def check_service_health(url, max_attempts=30):
    """Check if a service is healthy."""
    import requests
    
    for i in range(max_attempts):
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    
    return False


def set_environment_variables():
    """Set environment variables for real service testing."""
    env_vars = {
        'USE_REAL_SERVICES': 'true',
        'BACKEND_URL': 'http://localhost:8000',
        'AUTH_SERVICE_URL': 'http://localhost:8081',
        'WEBSOCKET_URL': 'ws://localhost:8000',
        'DATABASE_URL': 'postgresql://netra_test:test_password@localhost:5433/netra_test',
        'REDIS_URL': 'redis://localhost:6380',
        'TEST_MODE': 'real'
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    print("Environment variables set for real service testing")


def main():
    parser = argparse.ArgumentParser(
        description="Start test services for frontend real service testing"
    )
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Use Docker services instead of local processes"
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait for services to be healthy"
    )
    
    args = parser.parse_args()
    
    # Set environment variables
    set_environment_variables()
    
    if args.docker:
        # Check Docker is running
        if not check_docker_running():
            print("Docker is not running. Please start Docker first.")
            return 1
        
        # Start Docker services
        if not start_docker_services():
            return 1
        
        if not args.no_wait:
            # Wait for Docker services to be healthy
            print("Waiting for Docker services to be healthy...")
            time.sleep(10)
    else:
        # Start local services
        if not start_local_services():
            return 1
    
    print("\nServices are ready for testing!")
    print("\nTo run frontend tests with real services:")
    print("  python unified_test_runner.py --category frontend --real-services")
    print("\nTo run all integration tests:")
    print("  python unified_test_runner.py --category integration --real-services --real-llm")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
