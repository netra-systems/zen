"""Service Discovery During Initial Bootstrap Critical Path Test - L3

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Platform Reliability
- Value Impact: Services must find each other to function
- Revenue Impact: $60K MRR - Service mesh coordination

Critical Path: Service registration -> Discovery -> Health monitoring -> Load balancing -> Failover
Coverage: Bootstrap sequence, service registry (Redis), discovery mechanisms, health integration, load balancing

This L3 test uses real Redis as service registry with multiple service instances
testing actual registration/discovery flow during system bootstrap.
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

import pytest

from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.logging_config import central_logger

from netra_backend.app.services.redis_service import RedisService

logger = central_logger.get_logger(__name__)

@dataclass
class ServiceInstance:
    """Service instance registration data."""
    service_name: str
    instance_id: str
    host: str
    port: int
    health_endpoint: str
    version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    registration_time: Optional[float] = None
    last_heartbeat: Optional[float] = None

@dataclass
class BootstrapMetrics:
    """Bootstrap performance metrics."""
    total_services: int = 0
    successful_registrations: int = 0
    failed_registrations: int = 0
    discovery_time_ms: float = 0.0
    registration_time_ms: float = 0.0
    health_check_time_ms: float = 0.0
    load_balancing_time_ms: float = 0.0
    errors: List[str] = field(default_factory=list)

class ServiceRegistry:
    """Redis-based service registry for L3 testing."""
    
    def __init__(self, redis_service: RedisService):
        self.redis = redis_service
        self.service_prefix = "service_registry:services"
        self.health_prefix = "service_registry:health"
        self.instances_prefix = "service_registry:instances"
        
    async def register_service(self, instance: ServiceInstance) -> Dict[str, Any]:
        """Register service instance in Redis registry."""
        registration_start = time.time()
        
        try:
            instance.registration_time = registration_start
            instance.last_heartbeat = registration_start
            
            # Register service instance
            instance_key = f"{self.instances_prefix}:{instance.service_name}:{instance.instance_id}"
            instance_data = {
                "service_name": instance.service_name,
                "instance_id": instance.instance_id,
                "host": instance.host,
                "port": instance.port,
                "health_endpoint": instance.health_endpoint,
                "version": instance.version,
                "metadata": json.dumps(instance.metadata),
                "tags": json.dumps(instance.tags),
                "registration_time": instance.registration_time,
                "last_heartbeat": instance.last_heartbeat,
                "status": "healthy"
            }
            
            # Store instance data
            await self.redis.client.hset(instance_key, mapping=instance_data)
            await self.redis.client.expire(instance_key, 300)  # 5 minute TTL
            
            # Add to service instances list
            service_instances_key = f"{self.service_prefix}:{instance.service_name}:instances"
            await self.redis.client.sadd(service_instances_key, instance.instance_id)
            await self.redis.client.expire(service_instances_key, 300)
            
            # Update service metadata
            service_key = f"{self.service_prefix}:{instance.service_name}"
            service_data = {
                "service_name": instance.service_name,
                "version": instance.version,
                "updated_at": time.time()
            }
            await self.redis.client.hset(service_key, mapping=service_data)
            await self.redis.client.expire(service_key, 300)
            
            registration_duration = (time.time() - registration_start) * 1000
            
            return {
                "success": True,
                "instance_id": instance.instance_id,
                "registration_time_ms": registration_duration,
                "registry_key": instance_key
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "registration_time_ms": (time.time() - registration_start) * 1000
            }
    
    async def discover_service_instances(self, service_name: str) -> Dict[str, Any]:
        """Discover all instances of a service."""
        discovery_start = time.time()
        
        try:
            # Get all instance IDs for the service
            service_instances_key = f"{self.service_prefix}:{service_name}:instances"
            instance_ids = await self.redis.client.smembers(service_instances_key)
            
            instances = []
            healthy_count = 0
            unhealthy_count = 0
            
            for instance_id in instance_ids:
                instance_key = f"{self.instances_prefix}:{service_name}:{instance_id}"
                instance_data = await self.redis.client.hgetall(instance_key)
                
                if instance_data:
                    # Parse JSON fields
                    try:
                        instance_data["metadata"] = json.loads(instance_data.get("metadata", "{}"))
                        instance_data["tags"] = json.loads(instance_data.get("tags", "[]"))
                    except json.JSONDecodeError:
                        instance_data["metadata"] = {}
                        instance_data["tags"] = []
                    
                    # Check health status
                    status = instance_data.get("status", "unknown")
                    if status == "healthy":
                        healthy_count += 1
                    else:
                        unhealthy_count += 1
                    
                    instances.append(instance_data)
            
            discovery_duration = (time.time() - discovery_start) * 1000
            
            return {
                "success": True,
                "service_name": service_name,
                "total_instances": len(instances),
                "healthy_instances": healthy_count,
                "unhealthy_instances": unhealthy_count,
                "instances": instances,
                "discovery_time_ms": discovery_duration
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "discovery_time_ms": (time.time() - discovery_start) * 1000
            }
    
    async def update_instance_health(self, service_name: str, instance_id: str, 
                                   status: str, health_data: Dict[str, Any] = None) -> bool:
        """Update health status of service instance."""
        try:
            instance_key = f"{self.instances_prefix}:{service_name}:{instance_id}"
            
            # Check if instance exists
            exists = await self.redis.client.exists(instance_key)
            if not exists:
                return False
            
            # Update health status and heartbeat
            update_data = {
                "status": status,
                "last_heartbeat": time.time()
            }
            
            if health_data:
                update_data["health_data"] = json.dumps(health_data)
            
            await self.redis.client.hset(instance_key, mapping=update_data)
            return True
            
        except Exception as e:
            logger.error(f"Failed to update instance health: {e}")
            return False
    
    async def unregister_service(self, service_name: str, instance_id: str) -> bool:
        """Unregister service instance."""
        try:
            # Remove from instances set
            service_instances_key = f"{self.service_prefix}:{service_name}:instances"
            await self.redis.client.srem(service_instances_key, instance_id)
            
            # Remove instance data
            instance_key = f"{self.instances_prefix}:{service_name}:{instance_id}"
            await self.redis.client.delete(instance_key)
            
            return True
        except Exception as e:
            logger.error(f"Failed to unregister service: {e}")
            return False

class LoadBalancer:
    """Simple load balancer for testing."""
    
    def __init__(self):
        self.request_counts = {}
        self.selection_strategy = "round_robin"
        
    async def select_instance(self, service_name: str, instances: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Select instance using load balancing strategy."""
        healthy_instances = [i for i in instances if i.get("status") == "healthy"]
        
        if not healthy_instances:
            return None
        
        if self.selection_strategy == "round_robin":
            # Simple round-robin based on request count
            service_key = f"{service_name}_requests"
            count = self.request_counts.get(service_key, 0)
            selected = healthy_instances[count % len(healthy_instances)]
            self.request_counts[service_key] = count + 1
            return selected
        
        # Default to first healthy instance
        return healthy_instances[0]

class ServiceDiscoveryBootstrapL3:
    """L3 Service Discovery Bootstrap test manager."""
    
    def __init__(self):
        self.redis_service = RedisService()
        self.service_registry = None
        self.load_balancer = LoadBalancer()
        self.registered_services: List[ServiceInstance] = []
        self.metrics = BootstrapMetrics()
        self.test_key_prefix = f"test_bootstrap_{uuid.uuid4().hex[:8]}"
        
    async def initialize(self):
        """Initialize Redis connection and service registry."""
        await self.redis_service.connect()
        self.service_registry = ServiceRegistry(self.redis_service)
        
        # Verify Redis connectivity
        ping_result = await self.redis_service.ping()
        if not ping_result:
            raise RuntimeError("Redis connection failed")
        
        logger.info("Service discovery bootstrap L3 initialized")
    
    async def simulate_bootstrap_sequence(self, service_configs: List[Dict[str, Any]]) -> BootstrapMetrics:
        """Simulate complete service bootstrap sequence."""
        bootstrap_start = time.time()
        
        try:
            self.metrics.total_services = len(service_configs)
            
            # Phase 1: Service Registration
            registration_results = await self._register_services_during_bootstrap(service_configs)
            
            # Phase 2: Service Discovery
            discovery_results = await self._test_service_discovery_after_bootstrap()
            
            # Phase 3: Health Check Integration
            health_results = await self._test_health_check_integration()
            
            # Phase 4: Load Balancing
            load_balancing_results = await self._test_load_balancing()
            
            # Phase 5: Failure Handling
            failure_results = await self._test_service_failure_handling()
            
            # Calculate total metrics
            total_time = (time.time() - bootstrap_start) * 1000
            self.metrics.registration_time_ms = sum(r.get("registration_time_ms", 0) for r in registration_results)
            
            logger.info(f"Bootstrap sequence completed in {total_time:.2f}ms")
            
        except Exception as e:
            self.metrics.errors.append(f"Bootstrap sequence failed: {str(e)}")
            logger.error(f"Bootstrap sequence error: {e}")
        
        return self.metrics
    
    async def _register_services_during_bootstrap(self, service_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Register multiple services during bootstrap."""
        registration_tasks = []
        
        for config in service_configs:
            instance = ServiceInstance(
                service_name=config["service_name"],
                instance_id=f"{config['service_name']}_{config.get('instance_id', uuid.uuid4().hex[:8])}",
                host=config.get("host", "localhost"),
                port=config.get("port", 8080),
                health_endpoint=config.get("health_endpoint", "/health"),
                version=config.get("version", "1.0.0"),
                metadata=config.get("metadata", {}),
                tags=config.get("tags", [])
            )
            
            self.registered_services.append(instance)
            task = self.service_registry.register_service(instance)
            registration_tasks.append(task)
        
        # Execute all registrations concurrently (as happens during bootstrap)
        results = await asyncio.gather(*registration_tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                self.metrics.failed_registrations += 1
                self.metrics.errors.append(f"Registration failed: {str(result)}")
            elif result.get("success"):
                self.metrics.successful_registrations += 1
            else:
                self.metrics.failed_registrations += 1
                self.metrics.errors.append(f"Registration failed: {result.get('error', 'Unknown error')}")
        
        return [r for r in results if not isinstance(r, Exception)]
    
    async def _test_service_discovery_after_bootstrap(self) -> List[Dict[str, Any]]:
        """Test service discovery after bootstrap registration."""
        discovery_start = time.time()
        
        # Get unique service names
        service_names = list(set(s.service_name for s in self.registered_services))
        
        discovery_tasks = [
            self.service_registry.discover_service_instances(service_name)
            for service_name in service_names
        ]
        
        results = await asyncio.gather(*discovery_tasks, return_exceptions=True)
        
        self.metrics.discovery_time_ms = (time.time() - discovery_start) * 1000
        
        # Validate discovery results
        for result in results:
            if isinstance(result, Exception):
                self.metrics.errors.append(f"Discovery failed: {str(result)}")
            elif not result.get("success"):
                self.metrics.errors.append(f"Discovery failed: {result.get('error', 'Unknown error')}")
        
        return [r for r in results if not isinstance(r, Exception)]
    
    async def _test_health_check_integration(self) -> Dict[str, Any]:
        """Test health check integration during bootstrap."""
        health_start = time.time()
        
        try:
            # Simulate health check updates for all instances
            health_updates = []
            
            for service in self.registered_services:
                # Simulate varying health states
                status = "healthy" if hash(service.instance_id) % 10 < 8 else "unhealthy"  # 80% healthy
                health_data = {
                    "status": status,
                    "timestamp": time.time(),
                    "checks": {
                        "database": status == "healthy",
                        "memory": True,
                        "disk": True
                    }
                }
                
                update_task = self.service_registry.update_instance_health(
                    service.service_name, service.instance_id, status, health_data
                )
                health_updates.append(update_task)
            
            # Execute all health updates
            update_results = await asyncio.gather(*health_updates, return_exceptions=True)
            
            successful_updates = sum(1 for r in update_results if r is True)
            
            self.metrics.health_check_time_ms = (time.time() - health_start) * 1000
            
            return {
                "success": True,
                "total_updates": len(health_updates),
                "successful_updates": successful_updates,
                "health_check_time_ms": self.metrics.health_check_time_ms
            }
            
        except Exception as e:
            self.metrics.errors.append(f"Health check integration failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _test_load_balancing(self) -> Dict[str, Any]:
        """Test load balancing across discovered instances."""
        load_balancing_start = time.time()
        
        try:
            # Get unique service names
            service_names = list(set(s.service_name for s in self.registered_services))
            
            load_balancing_results = {}
            
            for service_name in service_names:
                # Discover instances
                discovery_result = await self.service_registry.discover_service_instances(service_name)
                
                if not discovery_result.get("success"):
                    continue
                
                instances = discovery_result.get("instances", [])
                if not instances:
                    continue
                
                # Test load balancing over 10 requests
                instance_usage = {}
                for _ in range(10):
                    selected = await self.load_balancer.select_instance(service_name, instances)
                    if selected:
                        instance_id = selected["instance_id"]
                        instance_usage[instance_id] = instance_usage.get(instance_id, 0) + 1
                
                load_balancing_results[service_name] = {
                    "total_instances": len(instances),
                    "healthy_instances": len([i for i in instances if i.get("status") == "healthy"]),
                    "instance_usage": instance_usage,
                    "load_distribution": self._calculate_load_distribution(instance_usage)
                }
            
            self.metrics.load_balancing_time_ms = (time.time() - load_balancing_start) * 1000
            
            return {
                "success": True,
                "results": load_balancing_results,
                "load_balancing_time_ms": self.metrics.load_balancing_time_ms
            }
            
        except Exception as e:
            self.metrics.errors.append(f"Load balancing test failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _calculate_load_distribution(self, instance_usage: Dict[str, int]) -> Dict[str, float]:
        """Calculate load distribution percentages."""
        total_requests = sum(instance_usage.values())
        if total_requests == 0:
            return {}
        
        return {
            instance_id: (count / total_requests) * 100
            for instance_id, count in instance_usage.items()
        }
    
    async def _test_service_failure_handling(self) -> Dict[str, Any]:
        """Test service failure detection and removal."""
        try:
            if not self.registered_services:
                return {"success": True, "message": "No services to test failure handling"}
            
            # Pick first service instance to simulate failure
            failed_service = self.registered_services[0]
            
            # Mark instance as unhealthy
            await self.service_registry.update_instance_health(
                failed_service.service_name, failed_service.instance_id, "unhealthy",
                {"error": "Connection timeout", "last_check": time.time()}
            )
            
            # Test discovery excludes unhealthy instances
            discovery_result = await self.service_registry.discover_service_instances(failed_service.service_name)
            
            if discovery_result.get("success"):
                unhealthy_count = discovery_result.get("unhealthy_instances", 0)
                total_count = discovery_result.get("total_instances", 0)
                
                return {
                    "success": True,
                    "failed_instance_detected": unhealthy_count > 0,
                    "total_instances": total_count,
                    "unhealthy_instances": unhealthy_count
                }
            else:
                return {"success": False, "error": "Discovery failed during failure test"}
            
        except Exception as e:
            self.metrics.errors.append(f"Failure handling test failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def cleanup(self):
        """Clean up test resources."""
        try:
            # Unregister all test services
            for service in self.registered_services:
                await self.service_registry.unregister_service(
                    service.service_name, service.instance_id
                )
            
            # Clean up any test keys
            pattern = f"*{self.test_key_prefix}*"
            test_keys = await self.redis_service.client.keys(pattern)
            if test_keys:
                await self.redis_service.client.delete(*test_keys)
            
            # Disconnect Redis
            await self.redis_service.disconnect()
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

@pytest.fixture
async def service_discovery_bootstrap():
    """Fixture for service discovery bootstrap testing."""
    manager = ServiceDiscoveryBootstrapL3()
    await manager.initialize()
    yield manager
    await manager.cleanup()

@pytest.mark.asyncio
@pytest.mark.l3_realism
@pytest.mark.asyncio
async def test_service_discovery_during_initial_bootstrap_l3(service_discovery_bootstrap):
    """Test complete service discovery during initial bootstrap sequence."""
    manager = service_discovery_bootstrap
    
    # Define realistic service configuration for bootstrap
    service_configs = [
        {
            "service_name": "api_gateway",
            "instance_id": "gateway_1",
            "host": "10.0.1.10",
            "port": 8080,
            "health_endpoint": "/health",
            "version": "1.2.0",
            "metadata": {"region": "us-east-1", "zone": "a"},
            "tags": ["gateway", "api", "public"]
        },
        {
            "service_name": "api_gateway",
            "instance_id": "gateway_2",
            "host": "10.0.1.11",
            "port": 8080,
            "health_endpoint": "/health",
            "version": "1.2.0",
            "metadata": {"region": "us-east-1", "zone": "b"},
            "tags": ["gateway", "api", "public"]
        },
        {
            "service_name": "user_service",
            "instance_id": "user_1",
            "host": "10.0.2.10",
            "port": 8081,
            "health_endpoint": "/health",
            "version": "2.1.0",
            "metadata": {"region": "us-east-1", "zone": "a"},
            "tags": ["user", "auth", "internal"]
        },
        {
            "service_name": "notification_service",
            "instance_id": "notification_1",
            "host": "10.0.3.10",
            "port": 8082,
            "health_endpoint": "/health",
            "version": "1.0.0",
            "metadata": {"region": "us-east-1", "zone": "a"},
            "tags": ["notification", "async", "internal"]
        }
    ]
    
    # Execute bootstrap sequence
    metrics = await manager.simulate_bootstrap_sequence(service_configs)
    
    # Validate bootstrap success
    assert metrics.total_services == 4
    assert metrics.successful_registrations >= 3  # Allow 1 failure
    assert metrics.failed_registrations <= 1
    
    # Validate timing requirements (bootstrap must be fast)
    assert metrics.registration_time_ms < 5000  # 5 seconds max for registration
    assert metrics.discovery_time_ms < 2000     # 2 seconds max for discovery
    assert metrics.health_check_time_ms < 1000  # 1 second max for health checks
    assert metrics.load_balancing_time_ms < 500 # 500ms max for load balancing
    
    # Validate no critical errors
    critical_errors = [e for e in metrics.errors if "failed" in e.lower()]
    assert len(critical_errors) <= 1  # Allow 1 non-critical error

@pytest.mark.asyncio
@pytest.mark.l3_realism
@pytest.mark.asyncio
async def test_service_registration_within_time_limits_l3(service_discovery_bootstrap):
    """Test that services register within 5 seconds during bootstrap."""
    manager = service_discovery_bootstrap
    
    # Multiple service instances registering simultaneously
    service_configs = [
        {"service_name": f"service_{i}", "port": 8080 + i}
        for i in range(5)
    ]
    
    registration_start = time.time()
    metrics = await manager.simulate_bootstrap_sequence(service_configs)
    total_time = (time.time() - registration_start) * 1000
    
    # All services must register within 5 seconds
    assert total_time < 5000
    assert metrics.successful_registrations == 5
    assert metrics.registration_time_ms < 5000

@pytest.mark.asyncio
@pytest.mark.l3_realism
@pytest.mark.asyncio
async def test_service_discovery_returns_correct_endpoints_l3(service_discovery_bootstrap):
    """Test that discovery returns correct service endpoints."""
    manager = service_discovery_bootstrap
    
    # Register known service configuration
    service_configs = [
        {
            "service_name": "test_service",
            "instance_id": "test_1",
            "host": "192.168.1.100",
            "port": 9090,
            "health_endpoint": "/api/health",
            "version": "2.0.0"
        }
    ]
    
    await manager.simulate_bootstrap_sequence(service_configs)
    
    # Discover the service
    discovery_result = await manager.service_registry.discover_service_instances("test_service")
    
    assert discovery_result["success"] is True
    assert discovery_result["total_instances"] == 1
    assert discovery_result["healthy_instances"] == 1
    
    instance = discovery_result["instances"][0]
    assert instance["host"] == "192.168.1.100"
    assert int(instance["port"]) == 9090
    assert instance["health_endpoint"] == "/api/health"
    assert instance["version"] == "2.0.0"

@pytest.mark.asyncio
@pytest.mark.l3_realism
@pytest.mark.asyncio
async def test_health_status_propagation_l3(service_discovery_bootstrap):
    """Test that health status updates propagate correctly."""
    manager = service_discovery_bootstrap
    
    # Register service
    service_configs = [{"service_name": "health_test_service", "port": 8080}]
    await manager.simulate_bootstrap_sequence(service_configs)
    
    service_instance = manager.registered_services[0]
    
    # Update health status
    health_update_success = await manager.service_registry.update_instance_health(
        service_instance.service_name, service_instance.instance_id, "unhealthy",
        {"error": "Database connection failed", "timestamp": time.time()}
    )
    
    assert health_update_success is True
    
    # Verify health status is reflected in discovery
    discovery_result = await manager.service_registry.discover_service_instances(
        service_instance.service_name
    )
    
    assert discovery_result["success"] is True
    assert discovery_result["unhealthy_instances"] == 1
    assert discovery_result["healthy_instances"] == 0
    
    instance = discovery_result["instances"][0]
    assert instance["status"] == "unhealthy"

@pytest.mark.asyncio
@pytest.mark.l3_realism
@pytest.mark.asyncio
async def test_failed_services_removed_from_discovery_l3(service_discovery_bootstrap):
    """Test that failed services are properly removed from registry."""
    manager = service_discovery_bootstrap
    
    # Register multiple instances
    service_configs = [
        {"service_name": "failover_service", "instance_id": "instance_1", "port": 8080},
        {"service_name": "failover_service", "instance_id": "instance_2", "port": 8081}
    ]
    await manager.simulate_bootstrap_sequence(service_configs)
    
    # Mark one instance as failed
    failed_instance = manager.registered_services[0]
    await manager.service_registry.update_instance_health(
        failed_instance.service_name, failed_instance.instance_id, "unhealthy"
    )
    
    # Test load balancing excludes failed instance
    discovery_result = await manager.service_registry.discover_service_instances("failover_service")
    healthy_instances = [i for i in discovery_result["instances"] if i.get("status") == "healthy"]
    
    # Load balancer should only select healthy instances
    selected_instances = []
    for _ in range(5):
        selected = await manager.load_balancer.select_instance("failover_service", discovery_result["instances"])
        if selected:
            selected_instances.append(selected["instance_id"])
    
    # All selections should be from healthy instances only
    healthy_instance_ids = [i["instance_id"] for i in healthy_instances]
    assert all(instance_id in healthy_instance_ids for instance_id in selected_instances)

@pytest.mark.asyncio
@pytest.mark.l3_realism
@pytest.mark.asyncio
async def test_load_balancing_works_correctly_l3(service_discovery_bootstrap):
    """Test that load balancing distributes requests correctly."""
    manager = service_discovery_bootstrap
    
    # Register multiple instances of same service
    service_configs = [
        {"service_name": "load_balanced_service", "instance_id": f"instance_{i}", "port": 8080 + i}
        for i in range(3)
    ]
    await manager.simulate_bootstrap_sequence(service_configs)
    
    # Discover instances
    discovery_result = await manager.service_registry.discover_service_instances("load_balanced_service")
    instances = discovery_result["instances"]
    
    # Make multiple requests to test load balancing
    instance_usage = {}
    for _ in range(15):  # 15 requests across 3 instances
        selected = await manager.load_balancer.select_instance("load_balanced_service", instances)
        instance_id = selected["instance_id"]
        instance_usage[instance_id] = instance_usage.get(instance_id, 0) + 1
    
    # Verify reasonable distribution (each instance should get some requests)
    assert len(instance_usage) == 3  # All instances used
    usage_values = list(instance_usage.values())
    
    # No instance should get more than 60% of requests (allows for some imbalance)
    max_usage = max(usage_values)
    assert max_usage <= 9  # 60% of 15 requests

@pytest.mark.asyncio
@pytest.mark.l3_realism
@pytest.mark.asyncio
async def test_service_versions_handled_properly_l3(service_discovery_bootstrap):
    """Test that multiple service versions are handled correctly."""
    manager = service_discovery_bootstrap
    
    # Register different versions of same service
    service_configs = [
        {
            "service_name": "versioned_service",
            "instance_id": "v1_instance",
            "port": 8080,
            "version": "1.0.0",
            "tags": ["stable"]
        },
        {
            "service_name": "versioned_service", 
            "instance_id": "v2_instance",
            "port": 8081,
            "version": "2.0.0",
            "tags": ["beta"]
        }
    ]
    await manager.simulate_bootstrap_sequence(service_configs)
    
    # Discover service instances
    discovery_result = await manager.service_registry.discover_service_instances("versioned_service")
    
    assert discovery_result["success"] is True
    assert discovery_result["total_instances"] == 2
    
    instances = discovery_result["instances"]
    versions = [i["version"] for i in instances]
    
    assert "1.0.0" in versions
    assert "2.0.0" in versions
    
    # Verify instance metadata is preserved
    v1_instance = next(i for i in instances if i["version"] == "1.0.0")
    v2_instance = next(i for i in instances if i["version"] == "2.0.0")
    
    assert int(v1_instance["port"]) == 8080
    assert int(v2_instance["port"]) == 8081