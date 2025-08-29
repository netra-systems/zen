#!/usr/bin/env python3
"""
Check status of all Netra Docker infrastructure services.
Shows health status, port availability, and connectivity for both test and dev environments.
"""

import subprocess
import json
import sys
from typing import Dict, List, Tuple
import socket
import time
import os

# Fix Windows console encoding for ANSI colors
if sys.platform == "win32":
    os.system("")  # Enable ANSI escape sequences on Windows

# Service configurations
SERVICES = {
    "test": {
        "postgres": {"container": "netra-test-postgres", "port": 5432, "type": "PostgreSQL"},
        "redis": {"container": "netra-test-redis", "port": 6379, "type": "Redis"},
        "clickhouse": {"container": "netra-test-clickhouse", "port": 8123, "type": "ClickHouse"},
    },
    "dev": {
        "postgres": {"container": "netra-dev-postgres", "port": 5433, "type": "PostgreSQL"},
        "redis": {"container": "netra-dev-redis", "port": 6380, "type": "Redis"},
        "clickhouse": {"container": "netra-dev-clickhouse", "port": 8124, "type": "ClickHouse"},
    }
}

def check_container_status(container_name: str) -> Tuple[bool, str, str]:
    """Check if a Docker container is running and healthy."""
    try:
        # Check if container exists and is running
        result = subprocess.run(
            ["docker", "inspect", container_name],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            return False, "Not Found", "Container does not exist"
        
        container_info = json.loads(result.stdout)[0]
        state = container_info["State"]
        
        if not state["Running"]:
            return False, "Stopped", f"Container is {state['Status']}"
        
        # Check health status if available
        health = state.get("Health", {})
        health_status = health.get("Status", "no healthcheck")
        
        if health_status == "healthy":
            return True, "Healthy", "Container is running and healthy"
        elif health_status == "starting":
            return True, "Starting", "Container is starting up"
        elif health_status == "unhealthy":
            return False, "Unhealthy", "Container health check failed"
        else:
            return True, "Running", "Container is running (no health check)"
            
    except Exception as e:
        return False, "Error", str(e)

def check_port(port: int) -> bool:
    """Check if a port is accessible."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        result = sock.connect_ex(('localhost', port))
        return result == 0
    except:
        return False
    finally:
        sock.close()

def print_status_table():
    """Print a formatted status table of all services."""
    print("\n" + "="*80)
    print("NETRA DOCKER INFRASTRUCTURE STATUS (6 Services)")
    print("="*80)
    
    all_healthy = True
    services_count = 0
    
    for env in ["test", "dev"]:
        print(f"\n{env.upper()} ENVIRONMENT:")
        print("-"*60)
        print(f"{'Service':<15} {'Container':<25} {'Status':<12} {'Port':<8} {'Available'}")
        print("-"*60)
        
        for service_name, config in SERVICES[env].items():
            services_count += 1
            container_name = config["container"]
            port = config["port"]
            service_type = config["type"]
            
            # Check container status
            is_running, status, message = check_container_status(container_name)
            
            # Check port availability
            port_available = check_port(port) if is_running else False
            
            # Format status with color codes
            if status == "Healthy":
                status_display = f"\033[92m{status:<12}\033[0m"  # Green
            elif status == "Starting":
                status_display = f"\033[93m{status:<12}\033[0m"  # Yellow
            elif status in ["Running"]:
                status_display = f"\033[94m{status:<12}\033[0m"  # Blue
            else:
                status_display = f"\033[91m{status:<12}\033[0m"  # Red
                all_healthy = False
            
            port_display = f":{port}"
            available_display = "YES" if port_available else "NO"
            
            if not port_available and is_running:
                available_display = f"\033[93m{available_display}\033[0m"  # Yellow if running but port not available
            elif port_available:
                available_display = f"\033[92m{available_display}\033[0m"  # Green
            else:
                available_display = f"\033[91m{available_display}\033[0m"  # Red
            
            print(f"{service_type:<15} {container_name:<25} {status_display} {port_display:<8} {available_display}")
    
    print("\n" + "="*80)
    print(f"Total infrastructure services: {services_count}/6")
    
    # Quick start command
    if not all_healthy:
        print("\n>> TO START ALL SERVICES:")
        print("   docker-compose -f docker-compose.all.yml up -d")
        print("\n>> TO VIEW LOGS:")
        print("   docker-compose -f docker-compose.all.yml logs -f")
    else:
        print("\n[OK] All 6 infrastructure services are healthy and running!")
    
    print("\n>> TO RUN APPLICATION SERVICES LOCALLY:")
    print("   Backend:  cd netra_backend && uvicorn app.main:app --reload --port 8000")
    print("   Auth:     cd auth_service && uvicorn main:app --reload --port 8081")
    print("   Frontend: cd frontend && npm run dev")
    
    print("\n>> DOCUMENTATION:")
    print("   - Quick Start: README.md#quick-start")
    print("   - Detailed Guide: STARTUP_GUIDE.md")
    print("   - Docker Config: docker-compose.all.yml")
    print("="*80 + "\n")

def main():
    """Main entry point."""
    try:
        # Check if Docker is running
        result = subprocess.run(
            ["docker", "version"],
            capture_output=True,
            check=False
        )
        
        if result.returncode != 0:
            print("\n[ERROR] Docker is not running or not installed!")
            print("Please start Docker Desktop and try again.")
            sys.exit(1)
        
        print_status_table()
        
    except FileNotFoundError:
        print("\n[ERROR] Docker command not found!")
        print("Please install Docker: https://docs.docker.com/get-docker/")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Error checking services: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()