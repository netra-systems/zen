#!/usr/bin/env python
"""
Start backend and auth services for Podman environment
"""
import subprocess
import os
import sys
import time

def start_service(service_name, module_path, port):
    """Start a service using uvicorn"""
    env = os.environ.copy()
    
    # Common environment variables
    env.update({
        "ENVIRONMENT": "development",
        "LOG_LEVEL": "INFO",
        "PYTHONPATH": os.getcwd(),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
        
        # Database
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5433",
        "POSTGRES_USER": "netra",
        "POSTGRES_PASSWORD": "netra123",
        "POSTGRES_DB": "netra_dev",
        
        # Redis
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6380",
        
        # Secrets
        "JWT_SECRET_KEY": "dev-jwt-secret-key-must-be-at-least-32-characters",
        "SERVICE_SECRET": "test-secret-for-local-development-only-32chars",
    })
    
    if service_name == "backend":
        env.update({
            # ClickHouse
            "CLICKHOUSE_HOST": "localhost",
            "CLICKHOUSE_PORT": "9001",
            "CLICKHOUSE_USER": "netra",
            "CLICKHOUSE_PASSWORD": "netra123",
            "CLICKHOUSE_DB": "netra_analytics",
            
            # Auth Service
            "AUTH_SERVICE_URL": "http://localhost:8081",
            
            # Additional secrets
            "FERNET_KEY": "iZAG-Kz661gRuJXEGzxgghUFnFRamgDrjDXZE6HdJkw=",
            "SECRET_KEY": "dev-secret-key-for-development",
            
            # Memory settings
            "ENABLE_MEMORY_MONITORING": "false",
        })
    
    print(f"Starting {service_name} service on port {port}...")
    cmd = [
        sys.executable, "-m", "uvicorn", 
        module_path,
        "--host", "0.0.0.0",
        "--port", str(port),
        "--reload"
    ]
    
    return subprocess.Popen(cmd, env=env)

def wait_for_postgres():
    """Wait for PostgreSQL to be ready"""
    print("Waiting for PostgreSQL to be ready...")
    for i in range(30):
        result = subprocess.run(
            ["podman", "exec", "netra-postgres", "pg_isready", "-U", "netra"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("PostgreSQL is ready!")
            return True
        time.sleep(1)
    return False

def main():
    # Check if databases are running
    print("Checking database services...")
    result = subprocess.run(["podman", "ps", "--format", "{{.Names}}"], capture_output=True, text=True)
    containers = result.stdout.strip().split('\n')
    
    required = ["netra-postgres", "netra-redis", "netra-clickhouse"]
    missing = [c for c in required if c not in containers]
    
    if missing:
        print(f"Missing containers: {missing}")
        print("Please run: podman-compose up -d postgres redis clickhouse")
        sys.exit(1)
    
    # Wait for PostgreSQL
    if not wait_for_postgres():
        print("PostgreSQL is not ready after 30 seconds")
        sys.exit(1)
    
    # Start services
    processes = []
    
    # Start auth service first
    auth_proc = start_service("auth", "auth_service.app.main:app", 8081)
    processes.append(auth_proc)
    time.sleep(5)  # Give auth service time to start
    
    # Start backend service
    backend_proc = start_service("backend", "netra_backend.app.main:app", 8000)
    processes.append(backend_proc)
    
    print("\nServices started!")
    print("Auth service: http://localhost:8081")
    print("Backend service: http://localhost:8000")
    print("\nPress Ctrl+C to stop all services...")
    
    try:
        # Wait for processes
        for proc in processes:
            proc.wait()
    except KeyboardInterrupt:
        print("\nStopping services...")
        for proc in processes:
            proc.terminate()
        for proc in processes:
            proc.wait()
        print("Services stopped.")

if __name__ == "__main__":
    main()