#!/usr/bin/env python
"""Gradual Docker Startup Script for Windows

This script starts Docker services one by one with delays to prevent
resource exhaustion and Docker Desktop crashes on Windows.

Root Cause: Starting all services simultaneously creates a connection
storm through WSL2 that overwhelms Windows file descriptor limits.

Solution: Start services gradually with health checks between each.
"""

import os
import sys
import time
import subprocess
import platform
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

def check_docker_desktop():
    """Check if Docker Desktop is running on Windows."""
    if platform.system() != 'Windows':
        return True
    
    try:
        result = subprocess.run(
            ["sc", "query", "com.docker.service"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return "RUNNING" in result.stdout
    except Exception as e:
        print(f" FAIL:  Error checking Docker Desktop: {e}")
        return False

def wait_for_docker_desktop():
    """Wait for Docker Desktop to be ready."""
    print("[U+23F3] Waiting for Docker Desktop to be ready...")
    
    max_attempts = 30
    for attempt in range(max_attempts):
        if check_docker_desktop():
            # Additional check - can we actually run docker commands?
            try:
                result = subprocess.run(
                    ["docker", "version"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    print(" PASS:  Docker Desktop is ready")
                    return True
            except:
                pass
        
        if attempt < max_attempts - 1:
            print(f"  Attempt {attempt + 1}/{max_attempts} - Docker not ready, waiting 5 seconds...")
            time.sleep(5)
    
    print(" FAIL:  Docker Desktop failed to start")
    return False

def check_container_health(container_name):
    """Check if a container is healthy."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Health.Status}}", container_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip() == "healthy"
    except:
        return False

def start_service_gradually(service_name, compose_file="docker-compose.yml", delay=5):
    """Start a single Docker service and wait for it to be healthy."""
    print(f"\n[U+1F680] Starting {service_name}...")
    
    try:
        # Start the specific service
        cmd = [
            "docker-compose",
            "-f", compose_file,
            "up", "-d",
            "--no-deps",  # Don't start dependencies
            service_name
        ]
        
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f" FAIL:  Failed to start {service_name}")
            print(f"   Error: {result.stderr}")
            return False
        
        # Wait for the service to be healthy
        print(f"   Waiting {delay} seconds for {service_name} to stabilize...")
        time.sleep(delay)
        
        # Check container health
        container_name = f"netra-core-generation-1-dev-{service_name}-1"
        max_health_checks = 20
        
        for i in range(max_health_checks):
            if check_container_health(container_name):
                print(f" PASS:  {service_name} is healthy")
                return True
            
            if i < max_health_checks - 1:
                print(f"   Health check {i+1}/{max_health_checks} - waiting 3 seconds...")
                time.sleep(3)
        
        print(f" WARNING: [U+FE0F]  {service_name} started but health check timed out")
        return True  # Continue anyway
        
    except subprocess.TimeoutExpired:
        print(f" FAIL:  Timeout starting {service_name}")
        return False
    except Exception as e:
        print(f" FAIL:  Error starting {service_name}: {e}")
        return False

def start_all_services_gradually():
    """Start all Docker services in the correct order with delays."""
    
    # Service startup order (dependencies first)
    services = [
        ("redis", 3),      # Redis - fast startup
        ("postgres", 5),   # PostgreSQL - needs time to initialize
        ("clickhouse", 5), # ClickHouse - analytics DB
        ("auth", 5),       # Auth service depends on postgres
        ("backend", 10),   # Backend depends on all above
    ]
    
    print("=" * 60)
    print("GRADUAL DOCKER STARTUP FOR WINDOWS")
    print("=" * 60)
    print("This script starts services one by one to prevent crashes")
    print("Total estimated time: 2-3 minutes")
    print("=" * 60)
    
    # Check Docker Desktop first
    if not wait_for_docker_desktop():
        print("\n FAIL:  Docker Desktop is not running!")
        print("Please start Docker Desktop and try again.")
        return False
    
    # Start services one by one
    successful = []
    failed = []
    
    for service, delay in services:
        if start_service_gradually(service, delay=delay):
            successful.append(service)
        else:
            failed.append(service)
            print(f"\n WARNING: [U+FE0F]  Continuing despite {service} failure...")
    
    # Summary
    print("\n" + "=" * 60)
    print("STARTUP SUMMARY")
    print("=" * 60)
    print(f" PASS:  Successfully started: {', '.join(successful) if successful else 'None'}")
    
    if failed:
        print(f" FAIL:  Failed to start: {', '.join(failed)}")
        print("\nTo check logs for failed services:")
        for service in failed:
            print(f"  docker-compose logs {service}")
    
    # Final health check
    if successful:
        print("\n SEARCH:  Final health check...")
        time.sleep(3)
        
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            print(result.stdout)
            
            # Check backend health endpoint
            if "backend" in successful:
                import requests
                try:
                    response = requests.get("http://localhost:8000/health", timeout=2)
                    if response.status_code == 200:
                        print("\n PASS:  Backend health check passed!")
                    else:
                        print(f"\n WARNING: [U+FE0F]  Backend returned status {response.status_code}")
                except Exception as e:
                    print(f"\n WARNING: [U+FE0F]  Could not reach backend: {e}")
        except:
            pass
    
    return len(successful) > 0

def stop_all_services():
    """Stop all Docker services."""
    print("\n[U+1F6D1] Stopping all services...")
    
    try:
        result = subprocess.run(
            ["docker-compose", "down"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(" PASS:  All services stopped")
        else:
            print(f" WARNING: [U+FE0F]  Error stopping services: {result.stderr}")
    except Exception as e:
        print(f" FAIL:  Failed to stop services: {e}")

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Gradual Docker startup for Windows to prevent crashes"
    )
    parser.add_argument(
        "command",
        choices=["start", "stop", "restart"],
        help="Command to execute"
    )
    parser.add_argument(
        "--compose-file",
        default="docker-compose.yml",
        help="Docker Compose file to use (default: docker-compose.yml)"
    )
    
    args = parser.parse_args()
    
    if platform.system() != 'Windows':
        print(" WARNING: [U+FE0F]  This script is designed for Windows.")
        print("On other platforms, use: docker-compose up -d")
        
        if input("Continue anyway? (y/n): ").lower() != 'y':
            sys.exit(0)
    
    if args.command == "stop":
        stop_all_services()
    elif args.command == "restart":
        stop_all_services()
        time.sleep(5)
        success = start_all_services_gradually()
        sys.exit(0 if success else 1)
    else:  # start
        success = start_all_services_gradually()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()