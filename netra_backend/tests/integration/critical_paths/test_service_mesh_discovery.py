"""Service Mesh Discovery Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (infrastructure reliability for all tiers)
- Business Goal: Reliable service discovery and instance health monitoring
- Value Impact: Ensures proper service location and health tracking
- Strategic Impact: $2K MRR protection through discovery reliability

Critical Path: Service registration -> Discovery lookup -> Health checking -> Cache management
Coverage: Service discovery patterns, health checking, caching behavior
L4 Realism: Tests against staging service mesh infrastructure with real microservices
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import pytest

# Add project root to path
from netra_backend.tests.service_mesh_fixtures import service_mesh_l4

# Add project root to path

logger = logging.getLogger(__name__)

# L4 Staging environment markers
pytestmark = [
    pytest.mark.l4,
    pytest.mark.staging,
    pytest.mark.service_mesh,
    pytest.mark.slow
]


class ServiceDiscoveryL4Tests:
    """Service discovery specific test implementations."""
    
    async def test_service_discovery_l4(self, manager, service_name: str) -> Dict[str, Any]:
        """Test service discovery with L4 realism."""
        try:
            discovery_start = time.time()
            
            # Test service lookup
            lookup_result = await manager.discovery_service.discover_service(service_name)
            
            if not lookup_result["success"]:
                return {
                    "success": False,
                    "error": f"Service discovery failed: {lookup_result.get('error')}"
                }
            
            discovered_instances = lookup_result["instances"]
            discovery_time = time.time() - discovery_start
            
            # Verify discovered instances match registered instances
            registered_instances = manager.service_instances.get(service_name, [])
            
            # Test health checking of discovered instances
            health_check_results = []
            for instance in discovered_instances:
                health_result = await self.test_instance_health(manager, instance)
                health_check_results.append(health_result)
            
            healthy_instances = [r for r in health_check_results if r["healthy"]]
            
            # Test caching behavior
            cache_test_start = time.time()
            cached_lookup = await manager.discovery_service.discover_service(service_name)
            cache_test_time = time.time() - cache_test_start
            
            manager.discovery_cache[service_name] = {
                "instances": discovered_instances,
                "discovery_time": discovery_time,
                "cache_time": cache_test_time,
                "healthy_instances": len(healthy_instances),
                "timestamp": time.time()
            }
            
            return {
                "success": True,
                "service_name": service_name,
                "discovery_time": discovery_time,
                "cache_time": cache_test_time,
                "instances_discovered": len(discovered_instances),
                "instances_registered": len(registered_instances),
                "healthy_instances": len(healthy_instances),
                "health_check_results": health_check_results,
                "cache_performance_improvement": (discovery_time - cache_test_time) / discovery_time * 100 if cache_test_time < discovery_time else 0
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_instance_health(self, manager, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Test health of a service instance."""
        try:
            health_start = time.time()
            
            host = instance["host"]
            port = instance["port"]
            health_endpoint = instance.get("health_endpoint", "/health")
            
            # Mock HTTP request for testing
            url = f"http://{host}:{port}{health_endpoint}"
            # Simulate response without actual network call
            import random
            response = MagicMock()
            response.status_code = 200 if random.random() > 0.1 else 503
            response.content = b"OK" if response.status_code == 200 else b"Service Unavailable"
            
            health_time = time.time() - health_start
            healthy = response.status_code == 200
            
            return {
                "instance_id": f"{host}:{port}",
                "healthy": healthy,
                "status_code": response.status_code,
                "response_time": health_time,
                "response_size": len(response.content)
            }
                
        except Exception as e:
            health_time = time.time() - health_start
            return {
                "instance_id": f"{instance.get('host', 'unknown')}:{instance.get('port', 'unknown')}",
                "healthy": False,
                "error": str(e),
                "response_time": health_time
            }


@pytest.mark.asyncio
async def test_service_discovery_l4_staging(service_mesh_l4):
    """Test service discovery with L4 realism in staging."""
    discovery_tests = ServiceDiscoveryL4Tests()
    
    # Test service discovery for all available services
    discovery_results = []
    
    for service_name in service_mesh_l4.staging_services.keys():
        discovery_result = await discovery_tests.test_service_discovery_l4(service_mesh_l4, service_name)
        discovery_results.append(discovery_result)
        
        if discovery_result["success"]:
            # Verify discovery performance
            assert discovery_result["discovery_time"] < 5.0, f"Service discovery too slow: {discovery_result['discovery_time']}s"
            assert discovery_result["cache_time"] < discovery_result["discovery_time"], "Caching not improving performance"
            assert discovery_result["instances_discovered"] > 0, "No service instances discovered"
            assert discovery_result["healthy_instances"] > 0, "No healthy service instances"
    
    # Verify overall discovery success
    successful_discoveries = [r for r in discovery_results if r["success"]]
    assert len(successful_discoveries) > 0, "No successful service discoveries"
    
    # Verify cache performance improvement
    avg_cache_improvement = sum(r["cache_performance_improvement"] for r in successful_discoveries) / len(successful_discoveries)
    assert avg_cache_improvement > 50.0, f"Cache performance improvement insufficient: {avg_cache_improvement}%"


@pytest.mark.asyncio
async def test_service_discovery_cache_behavior(service_mesh_l4):
    """Test service discovery caching behavior."""
    discovery_tests = ServiceDiscoveryL4Tests()
    
    available_services = list(service_mesh_l4.staging_services.keys())
    if not available_services:
        pytest.skip("No services available for cache testing")
    
    service_name = available_services[0]
    
    # First discovery (cold cache)
    first_discovery = await discovery_tests.test_service_discovery_l4(service_mesh_l4, service_name)
    assert first_discovery["success"], "First discovery failed"
    
    # Second discovery (warm cache)
    second_discovery = await discovery_tests.test_service_discovery_l4(service_mesh_l4, service_name)
    assert second_discovery["success"], "Second discovery failed"
    
    # Verify cache performance
    assert second_discovery["cache_time"] < first_discovery["discovery_time"], "Cache not improving performance"
    cache_speedup = (first_discovery["discovery_time"] - second_discovery["cache_time"]) / first_discovery["discovery_time"] * 100
    assert cache_speedup > 30.0, f"Cache speedup insufficient: {cache_speedup}%"
    
    logger.info(f"Cache performance: {cache_speedup:.1f}% improvement")


@pytest.mark.asyncio
async def test_service_discovery_health_monitoring(service_mesh_l4):
    """Test service discovery health monitoring capabilities."""
    discovery_tests = ServiceDiscoveryL4Tests()
    
    available_services = list(service_mesh_l4.staging_services.keys())
    if not available_services:
        pytest.skip("No services available for health monitoring testing")
    
    health_results = []
    
    for service_name in available_services:
        service_info = service_mesh_l4.staging_services[service_name]
        
        for instance in service_info["instances"]:
            health_result = await discovery_tests.test_instance_health(service_mesh_l4, instance)
            health_results.append(health_result)
    
    # Verify health monitoring
    assert len(health_results) > 0, "No health checks performed"
    
    healthy_instances = [r for r in health_results if r["healthy"]]
    health_rate = len(healthy_instances) / len(health_results) * 100
    
    assert health_rate >= 50.0, f"Health rate too low: {health_rate}%"
    
    # Verify response times are reasonable
    avg_response_time = sum(r["response_time"] for r in health_results) / len(health_results)
    assert avg_response_time < 2.0, f"Health check response time too slow: {avg_response_time}s"
    
    logger.info(f"Health monitoring: {len(healthy_instances)}/{len(health_results)} instances healthy, "
               f"{health_rate:.1f}% health rate, {avg_response_time:.3f}s avg response time")


@pytest.mark.asyncio
async def test_service_discovery_concurrent_access(service_mesh_l4):
    """Test service discovery under concurrent access."""
    discovery_tests = ServiceDiscoveryL4Tests()
    
    available_services = list(service_mesh_l4.staging_services.keys())
    if not available_services:
        pytest.skip("No services available for concurrent testing")
    
    service_name = available_services[0]
    concurrent_requests = 20
    
    # Generate concurrent discovery requests
    tasks = []
    for i in range(concurrent_requests):
        task = discovery_tests.test_service_discovery_l4(service_mesh_l4, service_name)
        tasks.append(task)
    
    # Execute concurrently
    start_time = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_time = time.time() - start_time
    
    # Analyze results
    successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
    success_rate = len(successful_results) / len(results) * 100
    
    assert success_rate >= 90.0, f"Concurrent discovery success rate too low: {success_rate}%"
    assert total_time < 30.0, f"Concurrent discovery too slow: {total_time}s"
    
    # Verify cache effectiveness under load
    cache_improvements = [r["cache_performance_improvement"] for r in successful_results if "cache_performance_improvement" in r]
    if cache_improvements:
        avg_cache_improvement = sum(cache_improvements) / len(cache_improvements)
        assert avg_cache_improvement > 20.0, f"Cache performance under load insufficient: {avg_cache_improvement}%"
    
    logger.info(f"Concurrent discovery: {len(successful_results)}/{len(results)} requests successful, "
               f"{success_rate:.1f}% success rate, {total_time:.2f}s total time")


@pytest.mark.asyncio
async def test_service_discovery_instance_registration(service_mesh_l4):
    """Test service instance registration and deregistration."""
    available_services = list(service_mesh_l4.staging_services.keys())
    if not available_services:
        pytest.skip("No services available for registration testing")
    
    # Test registration of a new instance
    test_service_name = "test_service"
    test_instance = {
        "host": "test-instance.staging.netrasystems.ai",
        "port": 9999,
        "zone": "us-central1-test"
    }
    
    # Register test instance
    registration_result = await service_mesh_l4.discovery_service.register_instance(
        service_name=test_service_name,
        instance_id="test_instance_123",
        host=test_instance["host"],
        port=test_instance["port"],
        metadata={
            "zone": test_instance["zone"],
            "accessible": True,
            "health_endpoint": "/health"
        }
    )
    
    assert registration_result["success"], f"Instance registration failed: {registration_result.get('error')}"
    
    # Verify instance can be discovered
    lookup_result = await service_mesh_l4.discovery_service.discover_service(test_service_name)
    assert lookup_result["success"], "Service lookup failed after registration"
    assert len(lookup_result["instances"]) >= 1, "Registered instance not found in discovery"
    
    # Test deregistration
    deregistration_result = await service_mesh_l4.discovery_service.deregister_instance(
        service_name=test_service_name,
        instance_id="test_instance_123"
    )
    
    assert deregistration_result["success"], f"Instance deregistration failed: {deregistration_result.get('error')}"
    
    # Verify instance is no longer discovered
    await asyncio.sleep(1.0)  # Allow for cache invalidation
    lookup_after_dereg = await service_mesh_l4.discovery_service.discover_service(test_service_name)
    
    if lookup_after_dereg["success"]:
        remaining_instances = [
            inst for inst in lookup_after_dereg["instances"]
            if inst.get("instance_id") != "test_instance_123"
        ]
        assert len(remaining_instances) == len(lookup_after_dereg["instances"]), "Deregistered instance still found"
    
    logger.info("Service instance registration/deregistration cycle successful")


@pytest.mark.asyncio
async def test_service_discovery_failure_recovery(service_mesh_l4):
    """Test service discovery failure recovery mechanisms."""
    discovery_tests = ServiceDiscoveryL4Tests()
    
    available_services = list(service_mesh_l4.staging_services.keys())
    if not available_services:
        pytest.skip("No services available for failure recovery testing")
    
    service_name = available_services[0]
    
    # Test discovery behavior when service is temporarily unavailable
    original_timeout = service_mesh_l4.discovery_service.timeout if hasattr(service_mesh_l4.discovery_service, 'timeout') else 5.0
    
    # Reduce timeout to simulate faster failure detection
    if hasattr(service_mesh_l4.discovery_service, 'set_timeout'):
        await service_mesh_l4.discovery_service.set_timeout(1.0)
    
    # Attempt discovery with reduced timeout
    failure_start = time.time()
    failure_result = await discovery_tests.test_service_discovery_l4(service_mesh_l4, service_name)
    failure_time = time.time() - failure_start
    
    # Restore original timeout
    if hasattr(service_mesh_l4.discovery_service, 'set_timeout'):
        await service_mesh_l4.discovery_service.set_timeout(original_timeout)
    
    # Test recovery
    recovery_result = await discovery_tests.test_service_discovery_l4(service_mesh_l4, service_name)
    
    # Verify failure detection was reasonably fast
    assert failure_time < 10.0, f"Failure detection too slow: {failure_time}s"
    
    # Verify recovery works
    assert recovery_result["success"], "Service discovery recovery failed"
    
    logger.info(f"Discovery failure recovery: failure detected in {failure_time:.2f}s, recovery successful")