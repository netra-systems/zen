#!/usr/bin/env python3
"""
Unified Testing Environment Startup Script
Python equivalent of start-unified-tests.ps1 and start-unified-tests.sh

Purpose: One-command startup for complete testing environment.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional


# Configuration
COMPOSE_FILE = "docker-compose.test.yml"
ENV_FILE = ".env.test"
PROJECT_NAME = "netra-unified-test"

# Colors for terminal output
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    ENDC = '\033[0m'


def print_colored(message: str, color: str = Colors.ENDC):
    """Print colored output to terminal."""
    print(f"{color}{message}{Colors.ENDC}")


def print_status(message: str):
    """Print status message."""
    print_colored(f"[INFO] {message}", Colors.BLUE)


def print_success(message: str):
    """Print success message."""
    print_colored(f"[SUCCESS] {message}", Colors.GREEN)


def print_warning(message: str):
    """Print warning message."""
    print_colored(f"[WARNING] {message}", Colors.YELLOW)


def print_error(message: str):
    """Print error message."""
    print_colored(f"[ERROR] {message}", Colors.RED)


def run_command(cmd: List[str], check: bool = True, capture_output: bool = False, timeout: Optional[int] = None) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=True,
            timeout=timeout
        )
        return result
    except subprocess.CalledProcessError as e:
        if check:
            raise
        return e
    except subprocess.TimeoutExpired:
        print_error(f"Command timed out: {' '.join(cmd)}")
        raise


def check_docker() -> bool:
    """Check if Docker is running."""
    try:
        run_command(["docker", "info"], capture_output=True)
        print_success("Docker is running")
        return True
    except subprocess.CalledProcessError:
        print_error("Docker is not running. Please start Docker Desktop or Docker daemon.")
        return False


def check_docker_compose() -> str:
    """Check if docker-compose is available and return the command to use."""
    try:
        run_command(["docker-compose", "version"], capture_output=True)
        print_success("Docker Compose is available")
        return "docker-compose"
    except subprocess.CalledProcessError:
        try:
            run_command(["docker", "compose", "version"], capture_output=True)
            print_success("Docker Compose (v2) is available")
            return "docker compose"
        except subprocess.CalledProcessError:
            print_error("docker-compose or 'docker compose' not available")
            return ""


def check_config() -> bool:
    """Validate configuration files exist."""
    if not Path(COMPOSE_FILE).exists():
        print_error(f"Docker Compose file ({COMPOSE_FILE}) not found")
        return False
    
    if not Path(ENV_FILE).exists():
        print_error(f"Environment file ({ENV_FILE}) not found")
        return False
    
    print_success("Configuration files found")
    return True


def cleanup_containers(docker_compose_cmd: str) -> bool:
    """Cleanup existing containers."""
    print_status("Cleaning up existing containers...")
    
    try:
        cmd = docker_compose_cmd.split() + [
            "-f", COMPOSE_FILE, "--env-file", ENV_FILE,
            "down", "--volumes", "--remove-orphans"
        ]
        run_command(cmd)
        
        # Remove any dangling images
        try:
            run_command(["docker", "image", "prune", "-f"], capture_output=True)
        except subprocess.CalledProcessError:
            pass  # This is optional cleanup
        
        print_success("Cleanup completed")
        return True
    except subprocess.CalledProcessError:
        print_warning("Some cleanup operations failed (this may be normal)")
        return True  # Continue anyway


def build_images(docker_compose_cmd: str) -> bool:
    """Build Docker images."""
    print_status("Building Docker images...")
    
    try:
        cmd = docker_compose_cmd.split() + [
            "-f", COMPOSE_FILE, "--env-file", ENV_FILE,
            "build", "--no-cache"
        ]
        run_command(cmd)
        print_success("Images built successfully")
        return True
    except subprocess.CalledProcessError:
        print_error("Failed to build images")
        return False


def start_services(docker_compose_cmd: str) -> bool:
    """Start services in stages."""
    print_status("Starting unified test environment...")
    
    try:
        # Start databases first
        cmd = docker_compose_cmd.split() + [
            "-f", COMPOSE_FILE, "--env-file", ENV_FILE,
            "up", "-d", "test-postgres", "test-clickhouse", "test-redis"
        ]
        run_command(cmd)
        
        # Wait for databases to be ready
        print_status("Waiting for databases to be ready...")
        time.sleep(30)
        
        # Start application services
        cmd = docker_compose_cmd.split() + [
            "-f", COMPOSE_FILE, "--env-file", ENV_FILE,
            "up", "-d", "auth-service", "backend-service"
        ]
        run_command(cmd)
        
        # Wait for backend services
        print_status("Waiting for backend services...")
        time.sleep(30)
        
        # Start frontend
        cmd = docker_compose_cmd.split() + [
            "-f", COMPOSE_FILE, "--env-file", ENV_FILE,
            "up", "-d", "frontend-service"
        ]
        run_command(cmd)
        
        # Wait for frontend
        print_status("Waiting for frontend service...")
        time.sleep(20)
        
        print_success("All services started")
        return True
    except subprocess.CalledProcessError:
        print_error("Failed to start services")
        return False


def run_migrations(docker_compose_cmd: str) -> bool:
    """Run database migrations."""
    print_status("Running database migrations...")
    
    try:
        cmd = docker_compose_cmd.split() + [
            "-f", COMPOSE_FILE, "--env-file", ENV_FILE,
            "run", "--rm", "migration-runner"
        ]
        run_command(cmd)
        print_success("Migrations completed")
        return True
    except subprocess.CalledProcessError:
        print_warning("Migrations may have failed - continuing with tests")
        return True  # Continue anyway


def run_tests(docker_compose_cmd: str) -> bool:
    """Run the unified test suite."""
    print_status("Running unified test suite...")
    
    try:
        cmd = docker_compose_cmd.split() + [
            "-f", COMPOSE_FILE, "--env-file", ENV_FILE,
            "run", "--rm", "test-runner"
        ]
        run_command(cmd)
        
        # Create test results directory if it doesn't exist
        test_results_dir = Path("test_results_unified")
        test_results_dir.mkdir(exist_ok=True)
        
        print_success("Test results will be available in ./test_results_unified/")
        return True
    except subprocess.CalledProcessError:
        print_error("Tests failed or encountered errors")
        return False


def check_url(url: str, timeout: int = 5) -> bool:
    """Check if a URL is responding."""
    try:
        import urllib.request
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception:
        return False


def show_status(docker_compose_cmd: str) -> None:
    """Show service status and health checks."""
    print_status("Service Status:")
    
    try:
        cmd = docker_compose_cmd.split() + [
            "-f", COMPOSE_FILE, "--env-file", ENV_FILE, "ps"
        ]
        run_command(cmd)
    except subprocess.CalledProcessError:
        print_warning("Could not get service status")
    
    print("")
    print_status("Service Health Checks:")
    
    # Check PostgreSQL
    try:
        cmd = docker_compose_cmd.split() + [
            "-f", COMPOSE_FILE, "--env-file", ENV_FILE,
            "exec", "test-postgres", "pg_isready", "-U", "test_user"
        ]
        run_command(cmd, capture_output=True)
        print_success("PostgreSQL: Healthy")
    except subprocess.CalledProcessError:
        print_warning("PostgreSQL: Not Ready")
    
    # Check ClickHouse
    if check_url("http://localhost:8124/ping"):
        print_success("ClickHouse: Healthy")
    else:
        print_warning("ClickHouse: Not Ready")
    
    # Check Redis
    try:
        cmd = docker_compose_cmd.split() + [
            "-f", COMPOSE_FILE, "--env-file", ENV_FILE,
            "exec", "test-redis", "redis-cli", "-a", "test_password", "ping"
        ]
        run_command(cmd, capture_output=True)
        print_success("Redis: Healthy")
    except subprocess.CalledProcessError:
        print_warning("Redis: Not Ready")
    
    # Check Auth Service
    if check_url("http://localhost:8001/health"):
        print_success("Auth Service: Healthy")
    else:
        print_warning("Auth Service: Not Ready")
    
    # Check Backend Service
    if check_url("http://localhost:8000/health"):
        print_success("Backend Service: Healthy")
    else:
        print_warning("Backend Service: Not Ready")
    
    # Check Frontend Service
    if check_url("http://localhost:3000/api/health"):
        print_success("Frontend Service: Healthy")
    else:
        print_warning("Frontend Service: Not Ready")


def show_logs(docker_compose_cmd: str) -> None:
    """Show live logs."""
    try:
        cmd = docker_compose_cmd.split() + [
            "-f", COMPOSE_FILE, "--env-file", ENV_FILE, "logs", "-f"
        ]
        run_command(cmd)
    except KeyboardInterrupt:
        print_status("Log viewing stopped")
    except subprocess.CalledProcessError:
        print_error("Failed to show logs")


def main():
    """Main function to orchestrate the unified testing."""
    parser = argparse.ArgumentParser(description="Unified Testing Environment Startup")
    parser.add_argument("--build", action="store_true", help="Force rebuild of Docker images")
    parser.add_argument("--cleanup", action="store_true", help="Clean up containers and volumes before starting")
    parser.add_argument("--logs", action="store_true", help="Show live logs after starting services")
    parser.add_argument("--status", action="store_true", help="Show service status and health checks")
    parser.add_argument("--test-only", action="store_true", help="Only run tests (assume services are already running)")
    parser.add_argument("--stop", action="store_true", help="Stop all services")
    
    args = parser.parse_args()
    
    # Perform pre-flight checks
    if not check_docker():
        sys.exit(1)
    
    docker_compose_cmd = check_docker_compose()
    if not docker_compose_cmd:
        sys.exit(1)
    
    if not check_config():
        sys.exit(1)
    
    if args.stop:
        cleanup_containers(docker_compose_cmd)
        sys.exit(0)
    
    if args.status:
        show_status(docker_compose_cmd)
        sys.exit(0)
    
    if args.logs:
        show_logs(docker_compose_cmd)
        sys.exit(0)
    
    # Main execution flow
    print_status("Starting Netra Unified Testing Environment")
    print_colored("=" * 40, Colors.CYAN)
    
    try:
        success = True
        
        if args.cleanup:
            success &= cleanup_containers(docker_compose_cmd)
        
        if args.build:
            success &= build_images(docker_compose_cmd)
        
        if not args.test_only:
            success &= start_services(docker_compose_cmd)
            success &= run_migrations(docker_compose_cmd)
        
        # Wait a bit more for services to fully stabilize
        print_status("Allowing services to stabilize...")
        time.sleep(10)
        
        success &= run_tests(docker_compose_cmd)
        
        if args.logs:
            print_status("Showing live logs (Press Ctrl+C to exit)...")
            show_logs(docker_compose_cmd)
        else:
            if success:
                print_success("Unified testing completed!")
            else:
                print_warning("Testing completed with some issues")
            
            print_status(f"To view logs: {docker_compose_cmd} -f {COMPOSE_FILE} logs")
            print_status(f"To stop services: {docker_compose_cmd} -f {COMPOSE_FILE} down")
            show_status(docker_compose_cmd)
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print_status("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"An error occurred during execution: {e}")
        print_status(f"To stop services: {docker_compose_cmd} -f {COMPOSE_FILE} down")
        sys.exit(1)


if __name__ == "__main__":
    main()