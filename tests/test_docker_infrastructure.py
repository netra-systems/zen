#!/usr/bin/env python
"""Test script to verify Docker infrastructure integration."""

import asyncio
import logging
import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.real_services import DockerServiceManager, ServiceConfig
from test_framework.docker_port_discovery import DockerPortDiscovery

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_docker_service_detection():
    pass
"""Test Docker service detection and startup."""
print("")
=== Testing Docker Service Infrastructure ===
")"

    # Check Docker availability
docker_manager = DockerServiceManager()
print("")

if not docker_manager.docker_available:
    print("")
[X] Docker is not available. Please ensure Docker Desktop is running.")"
print("   Run: 'docker version' to verify Docker is working)"
return False

        # Check and start services
    print("")
[*] Checking Docker services...")"
port_mappings = docker_manager.check_and_start_services()

if port_mappings:
    print("")
[OK] Docker services discovered:")"
for service, port in port_mappings.items():
    print("")
else:
    print("")
[!] No Docker services found. Services may need to be started.")"
print("   Run: docker compose -f docker-compose.alpine-test.yml up -d)"

                    # Test port discovery
    print("")
[*] Testing port discovery...")"
port_discovery = DockerPortDiscovery()
all_ports = port_discovery.discover_all_ports()

print("")
Discovered service ports:")"
for service, mapping in all_ports.items():
    print("")
print("")
print("")

return True


    async def test_service_connections():
"""Test actual service connections."""
pass
print("")
=== Testing Service Connections ===
")"

from test_framework.real_services import RealServices

try:
                                # Create real services instance
services = RealServices()

                                # Check all services
    print("[*] Checking service availability...)"
await services.ensure_all_services_available()
print("[OK] All services are available!)"

                                # Test individual services
    print("")
[*] Testing individual services:")"

                                # Test PostgreSQL
async with services.postgres() as db:
result = await db.fetchval("SELECT 1)"
print("")

                                    # Test Redis
async with services.redis() as redis:
await redis.set("test_key", "test_value)"
value = await redis.get("test_key)"
print("")

                                        # Test ClickHouse
try:
    pass
result = await services.clickhouse.execute("SELECT 1)"
print("")
except Exception as e:
    print("")

await asyncio.sleep(0)
return True

except Exception as e:
    print("")
import traceback
traceback.print_exc()
return False


def main():
    pass
"""Main test function."""
print("= * 60)"
print("Docker Infrastructure Test Suite)"
print("= * 60)"

    # Test Docker detection
if not test_docker_service_detection():
    print("")
[!] Docker infrastructure test failed.")"
print("")
To fix:")"
print("1. Start Docker Desktop)"
print("2. Run: docker compose -f docker-compose.alpine-test.yml up -d)"
print("3. Re-run this test)"
return 1

        # Test service connections
    print("")
 + =" * 60)"
success = asyncio.run(test_service_connections())

if success:
    print("")
[OK] All infrastructure tests passed!")"
return 0
else:
    print("")
[X] Some infrastructure tests failed.")"
return 1


if __name__ == "__main__:"
    pass
sys.exit(main())
pass
