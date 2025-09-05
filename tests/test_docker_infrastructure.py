#!/usr/bin/env python
"""Test script to verify Docker infrastructure integration."""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.real_services import DockerServiceManager, ServiceConfig
from test_framework.docker_port_discovery import DockerPortDiscovery

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_docker_service_detection():
    """Test Docker service detection and startup."""
    print("\n=== Testing Docker Service Infrastructure ===\n")
    
    # Check Docker availability
    docker_manager = DockerServiceManager()
    print(f"Docker available: {docker_manager.docker_available}")
    
    if not docker_manager.docker_available:
        print("\n[X] Docker is not available. Please ensure Docker Desktop is running.")
        print("   Run: 'docker version' to verify Docker is working")
        return False
    
    # Check and start services
    print("\n[*] Checking Docker services...")
    port_mappings = docker_manager.check_and_start_services()
    
    if port_mappings:
        print("\n[OK] Docker services discovered:")
        for service, port in port_mappings.items():
            print(f"   - {service}: port {port}")
    else:
        print("\n[!] No Docker services found. Services may need to be started.")
        print("   Run: docker compose -f docker-compose.alpine-test.yml up -d")
    
    # Test port discovery
    print("\n[*] Testing port discovery...")
    port_discovery = DockerPortDiscovery()
    all_ports = port_discovery.discover_all_ports()
    
    print("\nDiscovered service ports:")
    for service, mapping in all_ports.items():
        print(f"   - {service}: {mapping.host}:{mapping.external_port} -> {mapping.internal_port}")
        print(f"     Container: {mapping.container_name}")
        print(f"     Available: {mapping.is_available}")
    
    return True


async def test_service_connections():
    """Test actual service connections."""
    print("\n=== Testing Service Connections ===\n")
    
    from test_framework.real_services import RealServices
    
    try:
        # Create real services instance
        services = RealServices()
        
        # Check all services
        print("[*] Checking service availability...")
        await services.ensure_all_services_available()
        print("[OK] All services are available!")
        
        # Test individual services
        print("\n[*] Testing individual services:")
        
        # Test PostgreSQL
        async with services.postgres() as db:
            result = await db.fetchval("SELECT 1")
            print(f"   PostgreSQL: [OK] (result: {result})")
        
        # Test Redis
        async with services.redis() as redis:
            await redis.set("test_key", "test_value")
            value = await redis.get("test_key")
            print(f"   Redis: [OK] (value: {value.decode() if value else 'None'})")
        
        # Test ClickHouse
        try:
            result = await services.clickhouse.execute("SELECT 1")
            print(f"   ClickHouse: [OK] (result: {result})")
        except Exception as e:
            print(f"   ClickHouse: [X] ({str(e)})")
        
        return True
        
    except Exception as e:
        print(f"\n[X] Error testing services: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    print("=" * 60)
    print("Docker Infrastructure Test Suite")
    print("=" * 60)
    
    # Test Docker detection
    if not test_docker_service_detection():
        print("\n[!] Docker infrastructure test failed.")
        print("\nTo fix:")
        print("1. Start Docker Desktop")
        print("2. Run: docker compose -f docker-compose.alpine-test.yml up -d")
        print("3. Re-run this test")
        return 1
    
    # Test service connections
    print("\n" + "=" * 60)
    success = asyncio.run(test_service_connections())
    
    if success:
        print("\n[OK] All infrastructure tests passed!")
        return 0
    else:
        print("\n[X] Some infrastructure tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())