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

# SSOT Docker Management - Use DockerTestUtility exclusively
from test_framework.ssot.docker import (
    DockerTestUtility,
    DockerTestEnvironmentType,
    create_docker_test_utility
)


class TestServiceCLI:
    """Command-line interface for managing test services."""
    
    def __init__(self):
        # Use SSOT DockerTestUtility for all Docker operations
        self.docker_utility = create_docker_test_utility(
            environment_type=DockerTestEnvironmentType.DEDICATED
        )
        
    async def start_services(self, e2e: bool = False, clickhouse: bool = False):
        """Start test services using SSOT DockerTestUtility."""
        print("[INFO] Starting test services...")
        
        # Initialize Docker utility
        async with self.docker_utility as docker:
            # Determine services to start
            services = ["postgres", "redis"]
            
            if e2e:
                services.extend(["backend", "auth"])
                print("[INFO] Starting E2E service stack...")
            
            if clickhouse:
                services.append("clickhouse")
                print("[INFO] Including ClickHouse service...")
            
            # Start services
            result = await docker.start_services(
                services=services,
                wait_for_health=True,
                timeout=120.0
            )
            
            if result["success"]:
                print("[SUCCESS] Test services started successfully!")
                await self.show_status()
            else:
                print(f"[ERROR] Failed to start test services: {result.get('errors')}")
                sys.exit(1)
    
    async def stop_services(self, clean: bool = False):
        """Stop test services using SSOT DockerTestUtility."""
        print("[INFO] Stopping test services...")
        
        async with self.docker_utility as docker:
            # Stop all running services
            result = await docker.stop_services()
            
            if result["success"]:
                if clean:
                    print("[SUCCESS] Test services stopped and data cleaned!")
                else:
                    print("[SUCCESS] Test services stopped!")
            else:
                print(f"[ERROR] Failed to stop test services: {result}")
                sys.exit(1)
    
    async def show_status(self):
        """Show status of test services using SSOT DockerTestUtility."""
        print("\n[TEST SERVICE STATUS]")
        print("-" * 50)
        
        async with self.docker_utility as docker:
            # Generate health report
            report = await docker.generate_health_report()
            
            if "error" in report:
                print(f"[ERROR] {report['error']}")
                return
            
            print(f"Environment: {report.get('environment', 'Unknown')}")
            print(f"Overall Health: {'[U+2713] Healthy' if report.get('overall_health') else '[U+2717] Unhealthy'}")
            print()
            
            # Show service details
            services = report.get('services', {})
            if services:
                for service_name, service_data in services.items():
                    health = service_data.get('health', {})
                    status_icon = "[U+2713]" if health.get('is_healthy') else "[U+2717]"
                    port = health.get('port', 'N/A')
                    response_time = health.get('response_time_ms', 0.0)
                    
                    print(f"{status_icon} {service_name:12} Port: {port:5} Response: {response_time:6.1f}ms")
                    
                    if health.get('error_message'):
                        print(f"   Error: {health['error_message']}")
                
                # Show service URLs
                print("\n[SERVICE URLS]")
                print("-" * 50)
                
                urls = docker.get_all_service_urls()
                for service_name, url in urls.items():
                    print(f"{service_name:12}: {url}")
            else:
                print("[INFO] No services are currently running")
    
    async def run_tests(self, pattern: Optional[str] = None):
        """Run tests using the Docker infrastructure."""
        print("[INFO] Running tests with Docker infrastructure...")
        
        # Ensure services are running
        await self.start_services()
        
        # Build test command
        cmd = ["python", "tests/unified_test_runner.py"]
        
        if pattern:
            cmd.extend(["--pattern", pattern])
        else:
            cmd.extend(["--categories", "integration", "--no-coverage", "--fast-fail"])
        
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