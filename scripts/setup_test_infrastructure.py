#!/usr/bin/env python3
"""
Test Infrastructure Setup Script

This script ensures that Redis and PostgreSQL services are available for integration tests.
Follows CLAUDE.md "Real Services Required" mandate - no mocks in integration tests.

Business Value: Development Velocity & Test Reliability
- Enables reliable integration testing with real services
- Reduces developer setup time and configuration drift
- Ensures consistent test environment across team

Usage:
    python scripts/setup_test_infrastructure.py --start
    python scripts/setup_test_infrastructure.py --status
    python scripts/setup_test_infrastructure.py --stop
"""

import asyncio
import subprocess
import sys
import time
import argparse
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestInfrastructureManager:
    """Manages test infrastructure services (Redis, PostgreSQL) for integration tests."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.compose_file = self.project_root / "docker" / "docker-compose.minimal-test.yml"
        self.services = ["minimal-test-redis", "minimal-test-postgres"]

    def run_command(self, command: list, cwd: Optional[Path] = None) -> tuple[int, str, str]:
        """Run a command and return exit code, stdout, stderr."""
        try:
            result = subprocess.run(
                command,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out after 60 seconds"
        except Exception as e:
            return 1, "", str(e)

    def is_docker_available(self) -> bool:
        """Check if Docker is available and running."""
        logger.info("Checking Docker availability...")

        # Check if docker command exists
        code, stdout, stderr = self.run_command(["docker", "--version"])
        if code != 0:
            logger.error("Docker not found in PATH. Please install Docker Desktop.")
            return False

        # Check if Docker daemon is running
        code, stdout, stderr = self.run_command(["docker", "ps"])
        if code != 0:
            logger.error("Docker daemon not running. Please start Docker Desktop.")
            return False

        logger.info(f"Docker available: {stdout.strip()}")
        return True

    def get_service_status(self) -> Dict[str, Any]:
        """Get status of test infrastructure services."""
        if not self.is_docker_available():
            return {"docker_available": False, "services": {}}

        # Get container status
        code, stdout, stderr = self.run_command([
            "docker-compose", "-f", str(self.compose_file), "ps", "--format", "json"
        ])

        status = {"docker_available": True, "services": {}}

        if code == 0 and stdout:
            try:
                # Parse docker-compose ps JSON output
                containers = json.loads(stdout) if stdout.startswith('[') else [json.loads(line) for line in stdout.strip().split('\n') if line]

                for service in self.services:
                    service_status = {
                        "running": False,
                        "healthy": False,
                        "port_accessible": False
                    }

                    # Find container for this service
                    for container in containers:
                        if service in container.get("Service", ""):
                            service_status["running"] = container.get("State") == "running"
                            service_status["healthy"] = "healthy" in container.get("Status", "").lower()
                            break

                    status["services"][service] = service_status

            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Could not parse docker-compose status: {e}")

        # Test port connectivity
        if "minimal-test-redis" in status["services"]:
            status["services"]["minimal-test-redis"]["port_accessible"] = self._test_redis_connection()

        if "minimal-test-postgres" in status["services"]:
            status["services"]["minimal-test-postgres"]["port_accessible"] = self._test_postgres_connection()

        return status

    def _test_redis_connection(self) -> bool:
        """Test Redis connection on port 6381."""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', 6381))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _test_postgres_connection(self) -> bool:
        """Test PostgreSQL connection on port 5436."""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', 5436))
            sock.close()
            return result == 0
        except Exception:
            return False

    def start_services(self) -> bool:
        """Start test infrastructure services."""
        if not self.is_docker_available():
            return False

        logger.info("Starting test infrastructure services...")

        # Start services with docker-compose
        code, stdout, stderr = self.run_command([
            "docker-compose", "-f", str(self.compose_file), "up", "-d"
        ] + self.services)

        if code != 0:
            logger.error(f"Failed to start services: {stderr}")
            return False

        logger.info("Services started, waiting for health checks...")

        # Wait for services to be healthy
        max_wait = 60  # 60 seconds timeout
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status = self.get_service_status()
            all_healthy = True

            for service, info in status.get("services", {}).items():
                if not (info["running"] and info["port_accessible"]):
                    all_healthy = False
                    break

            if all_healthy:
                logger.info("All services are healthy and accessible!")
                return True

            logger.info("Waiting for services to be ready...")
            time.sleep(5)

        logger.error("Services did not become healthy within 60 seconds")
        self.show_service_logs()
        return False

    def stop_services(self) -> bool:
        """Stop test infrastructure services."""
        if not self.is_docker_available():
            return False

        logger.info("Stopping test infrastructure services...")

        code, stdout, stderr = self.run_command([
            "docker-compose", "-f", str(self.compose_file), "down"
        ])

        if code != 0:
            logger.error(f"Failed to stop services: {stderr}")
            return False

        logger.info("Services stopped successfully")
        return True

    def show_service_logs(self):
        """Show recent logs from services for debugging."""
        logger.info("=== Service Logs (last 20 lines) ===")

        for service in self.services:
            logger.info(f"\n--- {service} logs ---")
            code, stdout, stderr = self.run_command([
                "docker-compose", "-f", str(self.compose_file), "logs", "--tail", "20", service
            ])

            if code == 0:
                print(stdout)
            else:
                logger.error(f"Could not get logs for {service}: {stderr}")

    def print_status(self):
        """Print detailed status of test infrastructure."""
        status = self.get_service_status()

        print("\n=== Test Infrastructure Status ===")
        print(f"Docker Available: {'✓' if status['docker_available'] else '✗'}")

        if not status['docker_available']:
            print("\n⚠️  Docker is not available. Please start Docker Desktop.")
            return

        print("\nServices:")
        for service, info in status.get("services", {}).items():
            service_name = service.replace("minimal-test-", "").title()
            running = "✓" if info["running"] else "✗"
            healthy = "✓" if info["healthy"] else "✗"
            accessible = "✓" if info["port_accessible"] else "✗"

            print(f"  {service_name:12} Running: {running}  Healthy: {healthy}  Accessible: {accessible}")

        # Check if ready for tests
        all_ready = all(
            info["running"] and info["port_accessible"]
            for info in status.get("services", {}).values()
        )

        if all_ready:
            print("\n✅ Infrastructure ready for integration tests!")
            print("\nRun tests with:")
            print("  python -m pytest tests/integration/test_3tier_persistence_integration.py -v")
        else:
            print("\n⚠️  Infrastructure not ready. Run:")
            print("  python scripts/setup_test_infrastructure.py --start")


def main():
    parser = argparse.ArgumentParser(
        description="Setup and manage test infrastructure for integration tests"
    )
    parser.add_argument(
        "--start", action="store_true",
        help="Start test infrastructure services"
    )
    parser.add_argument(
        "--stop", action="store_true",
        help="Stop test infrastructure services"
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Show status of test infrastructure"
    )
    parser.add_argument(
        "--logs", action="store_true",
        help="Show service logs"
    )

    args = parser.parse_args()

    if not any([args.start, args.stop, args.status, args.logs]):
        # Default to status if no action specified
        args.status = True

    manager = TestInfrastructureManager()

    try:
        if args.start:
            success = manager.start_services()
            sys.exit(0 if success else 1)

        elif args.stop:
            success = manager.stop_services()
            sys.exit(0 if success else 1)

        elif args.logs:
            manager.show_service_logs()
            sys.exit(0)

        elif args.status:
            manager.print_status()
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()