#!/usr/bin/env python3
"""Run E2E Tests with Docker-Compose Test Services

This script manages the lifecycle of Docker test services and runs E2E tests
with proper port configuration.

BVJ:
- Segment: Platform/Internal  
- Business Goal: Ensure reliable E2E testing with Docker services
- Value Impact: Prevents production bugs through comprehensive testing
- Strategic Impact: Enables CI/CD reliability and parallel testing
"""

import os
import sys
import subprocess
import time
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_command(cmd, capture=False):
    """Run a command and optionally capture output"""
    print(f"Running: {' '.join(cmd)}")
    if capture:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result
    else:
        return subprocess.run(cmd)


def start_docker_services():
    """Start Docker test services"""
    print("\n🐳 Starting Docker test services...")
    
    # Start test services using docker-compose
    cmd = ["docker-compose", "-f", "docker-compose.test.yml", "up", "-d",
           "--profile", "e2e"]
    result = run_command(cmd)
    
    if result.returncode != 0:
        print("❌ Failed to start Docker services")
        return False
    
    print("✅ Docker services started")
    return True


def wait_for_services():
    """Wait for Docker services to be ready"""
    print("\n⏳ Waiting for services to be ready...")
    
    # Use the setup script to wait for services
    cmd = ["python", "scripts/setup_e2e_test_ports.py", "--mode", "docker", 
           "--export", "--wait"]
    result = run_command(cmd)
    
    if result.returncode != 0:
        print("❌ Services did not become ready in time")
        return False
        
    print("✅ All services are ready")
    return True


def run_e2e_tests(test_path=None, markers=None, verbose=False):
    """Run E2E tests with proper configuration"""
    print("\n🧪 Running E2E tests...")
    
    # Set environment for Docker testing
    os.environ["DOCKER_CONTAINER"] = "true"
    os.environ["TEST_BACKEND_PORT"] = "8001"
    os.environ["TEST_AUTH_PORT"] = "8082"
    os.environ["TEST_FRONTEND_PORT"] = "3001"
    os.environ["TEST_POSTGRES_PORT"] = "5433"
    os.environ["TEST_REDIS_PORT"] = "6380"
    os.environ["TEST_CLICKHOUSE_PORT"] = "8124"
    
    # Build pytest command
    cmd = ["pytest"]
    
    if test_path:
        cmd.append(test_path)
    else:
        cmd.append("tests/e2e")
    
    if markers:
        cmd.extend(["-m", markers])
    
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    # Add other useful options
    cmd.extend([
        "--tb=short",
        "--disable-warnings",
        "-x"  # Stop on first failure
    ])
    
    result = run_command(cmd)
    return result.returncode == 0


def stop_docker_services():
    """Stop Docker test services"""
    print("\n🛑 Stopping Docker test services...")
    
    cmd = ["docker-compose", "-f", "docker-compose.test.yml", "down", "-v"]
    result = run_command(cmd)
    
    if result.returncode != 0:
        print("⚠️  Failed to stop some Docker services")
    else:
        print("✅ Docker services stopped")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run E2E tests with Docker services")
    parser.add_argument("test_path", nargs="?", help="Specific test path to run")
    parser.add_argument("-m", "--markers", help="Pytest markers to filter tests")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--keep-services", action="store_true", 
                       help="Keep Docker services running after tests")
    parser.add_argument("--no-start", action="store_true",
                       help="Don't start services (assume already running)")
    
    args = parser.parse_args()
    
    success = True
    services_started = False
    
    try:
        # Start services if not disabled
        if not args.no_start:
            if not start_docker_services():
                return 1
            services_started = True
            
            # Wait for services to be ready
            if not wait_for_services():
                return 1
        
        # Run the tests
        if not run_e2e_tests(args.test_path, args.markers, args.verbose):
            success = False
            
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        success = False
        
    finally:
        # Stop services unless asked to keep them
        if services_started and not args.keep_services:
            stop_docker_services()
    
    if success:
        print("\n✅ E2E tests completed successfully!")
        return 0
    else:
        print("\n❌ E2E tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())