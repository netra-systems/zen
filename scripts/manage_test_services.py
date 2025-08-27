#!/usr/bin/env python3
"""
Test Service Management Script

This script manages Docker Compose test services for the Netra platform.
It provides a simple interface to start, stop, and manage test infrastructure.

Usage:
    python scripts/manage_test_services.py start          # Start core test services
    python scripts/manage_test_services.py start --e2e    # Start full E2E stack
    python scripts/manage_test_services.py stop           # Stop all test services
    python scripts/manage_test_services.py status         # Check service status
    python scripts/manage_test_services.py clean          # Stop and clean all data
"""

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(parent_dir))

from test_framework.docker_test_manager import DockerTestManager, ServiceMode


class TestServiceCLI:
    """Command-line interface for managing test services."""
    
    def __init__(self):
        self.manager = DockerTestManager()
        
    async def start_services(self, e2e: bool = False, clickhouse: bool = False):
        """Start test services."""
        print("[INFO] Starting test services...")
        
        # Configure environment
        self.manager.configure_test_environment()
        
        # Determine services and profiles
        services = ["postgres-test", "redis-test"]
        profiles = []
        
        if e2e:
            services.extend(["backend-test", "auth-test"])
            profiles.append("e2e")
            print("[INFO] Starting E2E service stack...")
        
        if clickhouse:
            profiles.append("clickhouse")
            print("[INFO] Including ClickHouse service...")
        
        # Start services
        success = await self.manager.start_services(
            services=services,
            profiles=profiles,
            wait_healthy=True,
            timeout=120
        )
        
        if success:
            print("[SUCCESS] Test services started successfully!")
            await self.show_status()
        else:
            print("[ERROR] Failed to start test services")
            sys.exit(1)
    
    async def stop_services(self, clean: bool = False):
        """Stop test services."""
        print("[INFO] Stopping test services...")
        
        success = await self.manager.stop_services(cleanup_volumes=clean)
        
        if success:
            if clean:
                print("[SUCCESS] Test services stopped and data cleaned!")
            else:
                print("[SUCCESS] Test services stopped!")
        else:
            print("[ERROR] Failed to stop test services")
            sys.exit(1)
    
    async def show_status(self):
        """Show status of test services."""
        print("\n[TEST SERVICE STATUS]")
        print("-" * 50)
        
        # Check Docker availability
        if not self.manager.is_docker_available():
            print("[ERROR] Docker is not available")
            return
        
        # Get container status
        result = subprocess.run(
            [
                "docker", "compose",
                "-f", "docker-compose.test.yml",
                "-p", "netra-test",
                "ps", "--format", "table"
            ],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("[INFO] No test services are running")
        
        # Show service URLs
        print("\n[SERVICE URLS]")
        print("-" * 50)
        
        mode = self.manager.get_effective_mode()
        if mode == ServiceMode.DOCKER:
            print(f"PostgreSQL:  {self.manager.get_service_url('postgres')}")
            print(f"Redis:       {self.manager.get_service_url('redis')}")
            print(f"Backend:     {self.manager.get_service_url('backend')}")
            print(f"Auth:        {self.manager.get_service_url('auth')}")
        else:
            print(f"Mode: {mode.value}")
    
    async def run_tests(self, pattern: Optional[str] = None):
        """Run tests using the Docker infrastructure."""
        print("[INFO] Running tests with Docker infrastructure...")
        
        # Ensure services are running
        await self.start_services()
        
        # Build test command
        cmd = ["python", "unified_test_runner.py"]
        
        if pattern:
            cmd.extend(["--pattern", pattern])
        else:
            cmd.extend(["--level", "integration", "--no-coverage", "--fast-fail"])
        
        print(f"[INFO] Executing: {' '.join(cmd)}")
        
        # Run tests
        result = subprocess.run(cmd)
        sys.exit(result.returncode)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manage Docker Compose test services for Netra platform"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start test services")
    start_parser.add_argument(
        "--e2e",
        action="store_true",
        help="Start full E2E service stack (backend, auth)"
    )
    start_parser.add_argument(
        "--clickhouse",
        action="store_true",
        help="Include ClickHouse service"
    )
    
    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop test services")
    
    # Clean command
    clean_parser = subparsers.add_parser(
        "clean",
        help="Stop services and clean all data"
    )
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show service status")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.add_argument(
        "--pattern",
        help="Test pattern to run"
    )
    
    args = parser.parse_args()
    
    # Create CLI instance
    cli = TestServiceCLI()
    
    # Execute command
    if args.command == "start":
        await cli.start_services(e2e=args.e2e, clickhouse=args.clickhouse)
    elif args.command == "stop":
        await cli.stop_services(clean=False)
    elif args.command == "clean":
        await cli.stop_services(clean=True)
    elif args.command == "status":
        await cli.show_status()
    elif args.command == "test":
        await cli.run_tests(pattern=args.pattern)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)