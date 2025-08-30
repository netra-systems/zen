#!/usr/bin/env python3
"""
Launch DEV Environment for Local Development

This script starts the DEV environment Docker Compose stack with hot reload
for local development and manual testing.
"""

import os
import sys
import subprocess
import argparse
import time
import webbrowser
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
    """Stop any existing DEV environment containers."""
    print("Stopping existing DEV environment containers...")
    subprocess.run([
        "docker-compose",
        "-f", "docker-compose.dev.yml",
        "-f", "docker-compose.override.yml",
        "--env-file", ".env.dev",
        "down"
    ], cwd=Path(__file__).parent.parent)


def start_dev_environment(detached: bool = False, services: list = None, hot_reload: bool = True):
    """Start the DEV environment."""
    root_dir = Path(__file__).parent.parent
    
    # Check required ports
    required_ports = {
        5432: "PostgreSQL",
        6379: "Redis",
        8123: "ClickHouse HTTP",
        9000: "ClickHouse TCP",
        8000: "Backend",
        8081: "Auth",
        3000: "Frontend"
    }
    
    print("Checking port availability...")
    blocked_ports = []
    for port, service in required_ports.items():
        if services and service.lower() not in [s.lower() for s in services]:
            continue  # Skip checking ports for services we're not starting
        if not check_port_availability(port):
            blocked_ports.append(f"  - Port {port} ({service})")
    
    if blocked_ports:
        print("Error: The following DEV environment ports are already in use:")
        for port in blocked_ports:
            print(port)
        print("\nOptions:")
        print("1. Stop the conflicting services")
        print("2. Run: docker ps")
        print("3. Check if TEST environment is running (use different ports)")
        return False
    
    # Build command
    cmd = [
        "docker-compose",
        "-f", "docker-compose.dev.yml"
    ]
    
    # Add override file for hot reload if enabled
    if hot_reload and os.path.exists("docker-compose.override.yml"):
        cmd.extend(["-f", "docker-compose.override.yml"])
        print("Hot reload enabled via docker-compose.override.yml")
    
    cmd.extend([
        "--env-file", ".env.dev",
        "up"
    ])
    
    if detached:
        cmd.append("-d")
    
    # Add build flag for first run
    cmd.append("--build")
    
    if services:
        cmd.extend(services)
    else:
        # Default to backend and auth services
        cmd.extend(["--profile", "full"])
    
    # Start containers
    print("Starting DEV environment containers...")
    print(f"Command: {' '.join(cmd)}")
    
    if not detached:
        print("\nStarting in attached mode. Press Ctrl+C to stop.")
        print("Hot reload is enabled - file changes will automatically restart services.\n")
    
    result = subprocess.run(cmd, cwd=root_dir)
    
    if result.returncode != 0:
        print("Error: Failed to start DEV environment")
        return False
    
    if detached:
        print("\nDEV environment started successfully!")
        print("\nServices available at:")
        print("  - PostgreSQL: localhost:5432")
        print("  - Redis: localhost:6379")
        print("  - ClickHouse: localhost:8123")
        print("  - Backend API: http://localhost:8000")
        print("  - Auth Service: http://localhost:8081")
        print("  - Frontend: http://localhost:3000")
        print("\nHot reload is enabled - changes will be reflected automatically!")
        print("\nUseful commands:")
        print("  View logs: docker-compose -f docker-compose.dev.yml logs -f [service]")
        print("  Stop: docker-compose -f docker-compose.dev.yml down")
        print("  Restart service: docker-compose -f docker-compose.dev.yml restart [service]")
    
    return True


def wait_for_services(open_browser: bool = False):
    """Wait for all services to be healthy."""
    print("\nWaiting for services to be healthy...")
    
    max_attempts = 30
    backend_ready = False
    auth_ready = False
    frontend_ready = False
    
    for attempt in range(max_attempts):
        try:
            import requests
            
            # Check backend health
            if not backend_ready:
                response = requests.get("http://localhost:8000/health", timeout=2)
                if response.status_code == 200:
                    print("[OK] Backend is healthy!")
                    backend_ready = True
            
            # Check auth health
            if not auth_ready:
                response = requests.get("http://localhost:8081/health", timeout=2)
                if response.status_code == 200:
                    print("[OK] Auth service is healthy!")
                    auth_ready = True
            
            # Check frontend health
            if not frontend_ready:
                response = requests.get("http://localhost:3000", timeout=2)
                if response.status_code == 200:
                    print("[OK] Frontend is ready!")
                    frontend_ready = True
            
            if backend_ready and auth_ready:
                print("\n[OK] All core services are ready!")
                
                if open_browser and frontend_ready:
                    print("Opening browser to http://localhost:3000...")
                    webbrowser.open("http://localhost:3000")
                
                return True
                
        except Exception:
            pass
        
        time.sleep(2)
        print(f"Waiting... ({attempt + 1}/{max_attempts})")
    
    print("Warning: Some services may not be fully ready")
    return False


def view_logs(service: str = None):
    """View logs for DEV environment services."""
    cmd = [
        "docker-compose",
        "-f", "docker-compose.dev.yml",
        "logs", "-f"
    ]
    
    if service:
        cmd.append(service)
    
    subprocess.run(cmd, cwd=Path(__file__).parent.parent)


def main():
    parser = argparse.ArgumentParser(
        description="Launch DEV environment for local development with hot reload"
    )
    parser.add_argument(
        "--detach", "-d",
        action="store_true",
        help="Run in detached mode (background)"
    )
    parser.add_argument(
        "--services", "-s",
        nargs="+",
        help="Specific services to start (e.g., backend auth postgres)"
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop the DEV environment"
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Restart the DEV environment"
    )
    parser.add_argument(
        "--logs",
        nargs="?",
        const="all",
        help="View logs for services (optionally specify service name)"
    )
    parser.add_argument(
        "--no-hot-reload",
        action="store_true",
        help="Disable hot reload (don't use override file)"
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for services to be healthy"
    )
    parser.add_argument(
        "--open", "-o",
        action="store_true",
        help="Open browser when ready"
    )
    
    args = parser.parse_args()
    
    if not check_docker():
        sys.exit(1)
    
    if args.stop:
        stop_existing_containers()
        print("DEV environment stopped.")
        sys.exit(0)
    
    if args.logs:
        service = None if args.logs == "all" else args.logs
        view_logs(service)
        sys.exit(0)
    
    if args.restart:
        stop_existing_containers()
        time.sleep(2)
    
    # Start environment
    success = start_dev_environment(
        detached=args.detach,
        services=args.services,
        hot_reload=not args.no_hot_reload
    )
    
    if not success:
        sys.exit(1)
    
    if args.wait or args.open:
        wait_for_services(open_browser=args.open)


if __name__ == "__main__":
    main()