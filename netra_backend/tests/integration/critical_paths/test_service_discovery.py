"""Service Discovery and Registration Critical Path Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (microservice coordination)
- Business Goal: Reliable service mesh and microservice communication
- Value Impact: Protects $8K MRR from service discovery failures and communication breakdowns
- Strategic Impact: Enables scalable microservice architecture and service resilience

Critical Path: Service registration -> Discovery -> Health monitoring -> Load balancing -> Failover
Coverage: Service registry, discovery mechanisms, health integration, load balancing
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
import json
import logging
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from netra_backend.app.core.health.interface import HealthStatus

# Add project root to path
from netra_backend.app.core.health_checkers import HealthChecker
from netra_backend.app.redis_manager import RedisManager

# Add project root to path

logger = logging.getLogger(__name__)


class MockServiceRegistry:
    """Mock service registry for testing."""
    
    def __init__(self):
        self.services = {}
        self.instances = {}
        
    async def register_service(self, service_name: str, instance_config: Dict[str, Any]) -> Dict[str, Any]:
        """Register service instance."""
        if service_name not in self.services:
            self.services[service_name] = []
        
        instance_id = instance_config.get("instance_id", f"{service_name}_{len(self.services[service_name])}")
        instance_config["instance_id"] = instance_id
        
        self.services[service_name].append(instance_config)
        self.instances[instance_id] = instance_config
        
        return {"success": True, "instance_id": instance_id}
    
    async def unregister_service(self, service_name: str, instance_id: str) -> Dict[str, Any]:
        """Unregister service instance."""
        if service_name in self.services:
            self.services[service_name] = [
                inst for inst in self.services[service_name] 
                if inst.get("instance_id") != instance_id
            ]
        
        if instance_id in self.instances:
            del self.instances[instance_id]
        
        return {"success": True}
    
    async def discover_instances(self, service_name: str) -> List[Dict[str, Any]]:
        """Discover service instances."""
        return self.services.get(service_name, [])
    
    async def initialize(self):
        """Initialize registry."""
        pass
    
    async def shutdown(self):
        """Shutdown registry."""
        self.services.clear()
        self.instances.clear()


class MockLoadBalancer:
    """Mock load balancer for testing."""
    
    def __init__(self):
        self.algorithms = ["round_robin", "random", "least_connections"]
        self.current_index = 0
        
    async def select_instance(self, service_name: str, instances: List[Dict[str, Any]], 
                            algorithm: str = "round_robin") -> Dict[str, Any]:
        """Select instance using load balancing algorithm."""
        if not instances:
            return {"success": False, "error": "No instances available"}
        
        if algorithm == "round_robin":
            selected = instances[self.current_index % len(instances)]
            self.current_index += 1
        elif algorithm == "random":
            import random
            selected = random.choice(instances)
        else:  # least_connections
            selected = instances[0]  # Simplified for testing
        
        return {"success": True, "instance": selected}
    
    async def initialize(self):
        """Initialize load balancer."""
        pass
    
    async def shutdown(self):
        """Shutdown load balancer."""
        pass


class MockHealthService:
    """Mock health service for testing."""
    
    def __init__(self):
        self.health_status = {}
        self.registered_services = {}
        
    async def register_service_health(self, service_name: str, health_endpoint: str) -> Dict[str, Any]:
        """Register service for health monitoring."""
        self.registered_services[service_name] = health_endpoint
        return {"success": True}
    
    async def check_instance_health(self, service_name: str, instance_id: str) -> Dict[str, Any]:
        """Check health of service instance."""
        # Simulate mostly healthy instances
        import random
        is_healthy = random.random() > 0.1  # 90% healthy
        
        status = {
            "healthy": is_healthy,
            "status_code": 200 if is_healthy else 503,
            "response_time": random.uniform(0.01, 0.1)
        }
        
        self.health_status[instance_id] = status
        return status
    
    async def mark_instance_unhealthy(self, service_name: str, instance_id: str):
        """Mark instance as unhealthy."""
        self.health_status[instance_id] = {
            "healthy": False,
            "status_code": 503,
            "response_time": 0.0
        }
    
    async def start(self):
        """Start health service."""
        pass
    
    async def stop(self):
        """Stop health service."""
        self.health_status.clear()
        self.registered_services.clear()


class ServiceDiscoveryManager:
    """Manages service discovery and registration testing."""
    
    def __init__(self):
        self.discovery_service = None
        self.load_balancer = None
        self.health_service = None
        self.service_registry = None
        self.registered_services = []
        self.discovery_events = []
        
    async def initialize_services(self):
        """Initialize service discovery services."""
        self.service_registry = MockServiceRegistry()
        await self.service_registry.initialize()
        
        self.discovery_service = self.service_registry  # Use registry as discovery service
        
        self.load_balancer = MockLoadBalancer()
        await self.load_balancer.initialize()
        
        self.health_service = MockHealthService()
        await self.health_service.start()
    
    async def register_service_instance(self, service_name: str, instance_config: Dict[str, Any]) -> Dict[str, Any]:
        """Register service instance with discovery system."""
        registration_start = time.time()
        
        try:
            # Register with service registry
            registration_result = await self.service_registry.register_service(
                service_name, instance_config
            )
            
            # Register health check
            health_result = await self.health_service.register_service_health(
                service_name, instance_config.get("health_endpoint", "/health")
            )
            
            service_record = {
                "service_name": service_name,
                "instance_config": instance_config,
                "registry_success": registration_result.get("success", False),
                "discovery_success": registration_result.get("success", False),  # Same as registry
                "health_success": health_result.get("success", False),
                "registration_time": time.time() - registration_start
            }
            
            self.registered_services.append(service_record)
            return service_record
            
        except Exception as e:
            return {
                "service_name": service_name,
                "error": str(e),
                "registration_time": time.time() - registration_start,
                "registry_success": False
            }
    
    async def discover_service_instances(self, service_name: str) -> Dict[str, Any]:
        """Discover available instances of a service."""
        discovery_start = time.time()
        
        try:
            # Discover instances
            instances = await self.service_registry.discover_instances(service_name)
            
            # Get health status for each instance
            healthy_instances = []
            unhealthy_instances = []
            
            for instance in instances:
                health_status = await self.health_service.check_instance_health(
                    service_name, instance["instance_id"]
                )
                
                if health_status.get("healthy"):
                    healthy_instances.append(instance)
                else:
                    unhealthy_instances.append(instance)
            
            discovery_record = {
                "service_name": service_name,
                "total_instances": len(instances),
                "healthy_instances": len(healthy_instances),
                "unhealthy_instances": len(unhealthy_instances),
                "instances": instances,
                "discovery_time": time.time() - discovery_start
            }
            
            self.discovery_events.append(discovery_record)
            return discovery_record
            
        except Exception as e:
            return {
                "service_name": service_name,
                "error": str(e),
                "discovery_time": time.time() - discovery_start
            }
    
    async def test_load_balanced_service_calls(self, service_name: str, call_count: int) -> Dict[str, Any]:
        """Test load-balanced service calls through discovery."""
        load_test_start = time.time()
        
        # Discover available instances
        discovery_result = await self.discover_service_instances(service_name)
        available_instances = discovery_result.get("instances", [])
        
        if not available_instances:
            return {
                "service_name": service_name,
                "error": "No instances available",
                "load_test_time": time.time() - load_test_start
            }
        
        # Make load-balanced calls
        call_results = []
        instance_usage = {}
        
        for i in range(call_count):
            # Get instance via load balancer
            selected_result = await self.load_balancer.select_instance(
                service_name, available_instances
            )
            
            if not selected_result.get("success"):
                continue
                
            selected_instance = selected_result["instance"]
            
            # Track instance usage
            instance_id = selected_instance.get("instance_id")
            instance_usage[instance_id] = instance_usage.get(instance_id, 0) + 1
            
            # Simulate service call
            call_result = await self.simulate_service_call(selected_instance)
            call_results.append({
                "instance_id": instance_id,
                "call_success": call_result.get("success", False),
                "response_time": call_result.get("response_time", 0)
            })
        
        # Analyze load distribution
        total_calls = sum(instance_usage.values())
        load_distribution = {
            instance_id: (count / total_calls) * 100 
            for instance_id, count in instance_usage.items()
        }
        
        return {
            "service_name": service_name,
            "total_calls": call_count,
            "successful_calls": len([r for r in call_results if r["call_success"]]),
            "instance_usage": instance_usage,
            "load_distribution": load_distribution,
            "average_response_time": sum(r["response_time"] for r in call_results) / len(call_results),
            "load_test_time": time.time() - load_test_start
        }
    
    async def simulate_service_call(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate service call to instance."""
        call_start = time.time()
        
        # Simulate network call with variable response time
        await asyncio.sleep(0.01 + (hash(instance["instance_id"]) % 50) / 1000)
        
        return {
            "success": True,
            "response_time": time.time() - call_start,
            "instance_id": instance["instance_id"]
        }
    
    async def test_service_failover(self, service_name: str) -> Dict[str, Any]:
        """Test service failover when instances become unhealthy."""
        failover_start = time.time()
        
        # Get initial healthy instances
        initial_discovery = await self.discover_service_instances(service_name)
        healthy_instances = initial_discovery.get("healthy_instances", 0)
        
        if healthy_instances < 2:
            return {
                "service_name": service_name,
                "error": "Need at least 2 healthy instances for failover test",
                "failover_time": time.time() - failover_start
            }
        
        # Simulate instance failure
        instances = initial_discovery["instances"]
        failed_instance = instances[0]
        
        # Mark instance as unhealthy
        await self.health_service.mark_instance_unhealthy(
            service_name, failed_instance["instance_id"]
        )
        
        # Wait for health check propagation
        await asyncio.sleep(0.5)
        
        # Test service discovery after failure
        post_failure_discovery = await self.discover_service_instances(service_name)
        
        # Test load balancing excludes failed instance
        load_test = await self.test_load_balanced_service_calls(service_name, 10)
        
        # Check if failed instance was excluded
        failed_instance_id = failed_instance["instance_id"]
        failed_instance_used = failed_instance_id in load_test.get("instance_usage", {})
        
        return {
            "service_name": service_name,
            "initial_healthy": healthy_instances,
            "post_failure_healthy": post_failure_discovery.get("healthy_instances", 0),
            "failed_instance_excluded": not failed_instance_used,
            "failover_successful": (
                post_failure_discovery.get("healthy_instances", 0) == healthy_instances - 1 and
                not failed_instance_used
            ),
            "failover_time": time.time() - failover_start
        }
    
    async def cleanup(self):
        """Clean up service discovery test resources."""
        # Unregister all test services
        for service in self.registered_services:
            try:
                await self.service_registry.unregister_service(
                    service["service_name"], service["instance_config"]["instance_id"]
                )
            except Exception:
                pass
        
        if self.load_balancer:
            await self.load_balancer.shutdown()
        if self.health_service:
            await self.health_service.stop()
        if self.service_registry:
            await self.service_registry.shutdown()


@pytest.fixture
async def service_discovery_manager():
    """Create service discovery manager for testing."""
    manager = ServiceDiscoveryManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_service_registration_and_discovery(service_discovery_manager):
    """Test service registration and discovery flow."""
    manager = service_discovery_manager
    
    # Register multiple instances of a service
    service_instances = [
        {
            "instance_id": "api_service_1",
            "host": "10.0.1.10",
            "port": 8080,
            "health_endpoint": "/health"
        },
        {
            "instance_id": "api_service_2", 
            "host": "10.0.1.11",
            "port": 8080,
            "health_endpoint": "/health"
        }
    ]
    
    # Register instances
    registration_results = []
    for instance in service_instances:
        result = await manager.register_service_instance("api_service", instance)
        registration_results.append(result)
    
    # Verify registrations
    assert all(r["registry_success"] for r in registration_results)
    assert all(r["discovery_success"] for r in registration_results)
    assert all(r["registration_time"] < 1.0 for r in registration_results)
    
    # Test discovery
    discovery_result = await manager.discover_service_instances("api_service")
    
    assert discovery_result["total_instances"] == 2
    assert discovery_result["healthy_instances"] >= 1
    assert discovery_result["discovery_time"] < 0.5


@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_load_balanced_service_calls(service_discovery_manager):
    """Test load-balanced service calls through discovery."""
    manager = service_discovery_manager
    
    # Register service instances
    for i in range(3):
        await manager.register_service_instance(
            "load_test_service",
            {
                "instance_id": f"load_test_{i}",
                "host": f"10.0.1.{10+i}",
                "port": 8080,
                "health_endpoint": "/health"
            }
        )
    
    # Test load balancing
    load_test_result = await manager.test_load_balanced_service_calls(
        "load_test_service", 15
    )
    
    assert load_test_result["total_calls"] == 15
    assert load_test_result["successful_calls"] >= 14  # Allow for 1 failure
    assert load_test_result["average_response_time"] < 0.1
    assert load_test_result["load_test_time"] < 5.0
    
    # Verify load distribution (should be reasonably balanced)
    load_distribution = load_test_result["load_distribution"]
    distribution_values = list(load_distribution.values())
    
    # No single instance should handle more than 60% of traffic
    assert all(percentage <= 60.0 for percentage in distribution_values)


@pytest.mark.asyncio
@pytest.mark.l3_realism  
async def test_service_failover_mechanism(service_discovery_manager):
    """Test service failover when instances become unhealthy."""
    manager = service_discovery_manager
    
    # Register multiple instances
    for i in range(3):
        await manager.register_service_instance(
            "failover_test_service",
            {
                "instance_id": f"failover_test_{i}",
                "host": f"10.0.1.{20+i}",
                "port": 8080,
                "health_endpoint": "/health"
            }
        )
    
    # Test failover
    failover_result = await manager.test_service_failover("failover_test_service")
    
    assert failover_result["failover_successful"] is True
    assert failover_result["failed_instance_excluded"] is True
    assert failover_result["post_failure_healthy"] == failover_result["initial_healthy"] - 1
    assert failover_result["failover_time"] < 10.0


@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_service_discovery_performance(service_discovery_manager):
    """Test service discovery performance under load."""
    manager = service_discovery_manager
    
    # Register multiple services with multiple instances
    services = ["perf_service_a", "perf_service_b", "perf_service_c"]
    
    for service_name in services:
        for i in range(2):
            await manager.register_service_instance(
                service_name,
                {
                    "instance_id": f"{service_name}_{i}",
                    "host": f"10.0.2.{i+10}",
                    "port": 8080,
                    "health_endpoint": "/health"
                }
            )
    
    # Test concurrent discovery
    discovery_start = time.time()
    discovery_tasks = [
        manager.discover_service_instances(service_name)
        for service_name in services * 3  # 3 discovery calls per service
    ]
    
    discovery_results = await asyncio.gather(*discovery_tasks)
    total_discovery_time = time.time() - discovery_start
    
    # Verify performance
    assert total_discovery_time < 5.0  # All discoveries in 5 seconds
    assert all(r.get("total_instances", 0) == 2 for r in discovery_results)
    assert all(r.get("discovery_time", float('inf')) < 2.0 for r in discovery_results)