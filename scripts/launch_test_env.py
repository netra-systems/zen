#!/usr/bin/env python3
"""
Launch TEST Environment for Automated Testing

This script starts the TEST environment Docker Compose stack with proper configuration
for running automated tests with real services.
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_docker():
    """Check if Docker is installed and running."""
    try:
        subprocess.run(["docker", "--version"], capture_output=True, check=True)
        subprocess.run(["docker-compose", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: Docker or docker-compose is not installed or not running.")
        print("Please install Docker and ensure it's running.")
        return False


def check_port_availability(port: int) -> bool:
    """Check if a port is available."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result != 0


def stop_existing_containers():
    """Stop any existing TEST environment containers."""
    print("Stopping existing TEST environment containers...")
    subprocess.run([
        "docker-compose", 
        "-f", "docker-compose.test.yml",
        "--env-file", ".env.test",
        "down", "-v"
    ], cwd=Path(__file__).parent.parent)


def start_test_environment(detached: bool = True, services: list = None):
    """Start the TEST environment."""
    root_dir = Path(__file__).parent.parent
    
    # Check required ports
    required_ports = {
        5433: "PostgreSQL",
        6380: "Redis", 
        8124: "ClickHouse HTTP",
        9001: "ClickHouse TCP",
        8001: "Backend",
        8082: "Auth",
        3001: "Frontend"
    }
    
    print("Checking port availability...")
    blocked_ports = []
    for port, service in required_ports.items():
        if not check_port_availability(port):
            blocked_ports.append(f"  - Port {port} ({service})")
    
    if blocked_ports:
        print("Error: The following TEST environment ports are already in use:")
        for port in blocked_ports:
            print(port)
        print("\nOptions:")
        print("1. Stop the conflicting services")
        print("2. Run: docker ps")
        print("3. Check if DEV environment is using these ports")
        return False
    
    # Build command
    cmd = [
        "docker-compose",
        "-f", "docker-compose.test.yml",
        "--env-file", ".env.test",
        "up"
    ]
    
    if detached:
        cmd.append("-d")
    
    if services:
        cmd.extend(services)
    
    # Start containers
    print("Starting TEST environment containers...")
    print(f"Command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, cwd=root_dir)
    
    if result.returncode != 0:
        print("Error: Failed to start TEST environment")
        return False
    
    if detached:
        print("\nTEST environment started successfully!")
        print("\nServices available at:")
        print("  - PostgreSQL: localhost:5433")
        print("  - Redis: localhost:6380")
        print("  - ClickHouse: localhost:8124")
        print("  - Backend API: http://localhost:8001")
        print("  - Auth Service: http://localhost:8082")
        print("  - Frontend: http://localhost:3001")
        print("\nTo view logs: docker-compose -f docker-compose.test.yml logs -f")
        print("To stop: docker-compose -f docker-compose.test.yml down")
    
    return True


def wait_for_services():
    """Wait for all services to be healthy."""
    print("\nWaiting for services to be healthy...")
    
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            # Check backend health
            import requests
            response = requests.get("http://localhost:8001/health", timeout=2)
            if response.status_code == 200:
                print("Backend is healthy!")
                
                # Check auth health
                response = requests.get("http://localhost:8082/health", timeout=2)
                if response.status_code == 200:
                    print("Auth service is healthy!")
                    return True
        except Exception:
            pass
        
        time.sleep(2)
        print(f"Waiting... ({attempt + 1}/{max_attempts})")
    
    print("Warning: Services may not be fully ready")
    return False


def run_tests(category: str = "integration"):
    """Run tests against the TEST environment."""
    print(f"\nRunning {category} tests...")
    
    cmd = [
        "python", "unified_test_runner.py",
        "--category", category,
        "--no-coverage",
        "--fast-fail"
    ]
    
    subprocess.run(cmd, cwd=Path(__file__).parent.parent)


def main():
    parser = argparse.ArgumentParser(
        description="Launch TEST environment for automated testing"
    )
    parser.add_argument(
        "--attach", "-a",
        action="store_true",
        help="Run in attached mode (see logs)"
    )
    parser.add_argument(
        "--services", "-s",
        nargs="+",
        help="Specific services to start (e.g., postgres-test redis-test)"
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop the TEST environment"
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Restart the TEST environment"
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run tests after starting environment"
    )
    parser.add_argument(
        "--test-category",
        default="integration",
        help="Test category to run (default: integration)"
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for services to be healthy"
    )
    
    args = parser.parse_args()
    
    if not check_docker():
        sys.exit(1)
    
    if args.stop:
        stop_existing_containers()
        print("TEST environment stopped.")
        sys.exit(0)
    
    if args.restart:
        stop_existing_containers()
        time.sleep(2)
    
    # Start environment
    success = start_test_environment(
        detached=not args.attach,
        services=args.services
    )
    
    if not success:
        sys.exit(1)
    
    if args.wait or args.run_tests:
        wait_for_services()
    
    if args.run_tests:
        run_tests(args.test_category)


if __name__ == "__main__":
    main()