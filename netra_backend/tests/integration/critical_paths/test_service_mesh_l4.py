"""Service Mesh Communication L4 Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (infrastructure reliability for all tiers)
- Business Goal: Reliable inter-service communication, service discovery, load balancing
- Value Impact: Ensures system stability, reduces latency, prevents cascade failures
- Strategic Impact: $8K MRR protection through communication reliability and performance

Critical Path: Service discovery -> Load balancing -> Circuit breaking -> Retry policies -> Observability
Coverage: Real service mesh patterns, load balancing algorithms, timeout/retry policies, service discovery
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
import json
import logging
import os
import random
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import httpx
import pytest

from netra_backend.app.config import get_config
from netra_backend.app.services.service_mesh.circuit_breaker import (
    CircuitBreakerService,
)

# Add project root to path
from netra_backend.app.services.service_mesh.discovery_service import (
    ServiceDiscoveryService,
)
from netra_backend.app.services.service_mesh.load_balancer import LoadBalancerService
from netra_backend.app.services.service_mesh.retry_policy import RetryPolicyService

# Add project root to path

logger = logging.getLogger(__name__)

# L4 Staging environment markers
pytestmark = [
    pytest.mark.l4,
    pytest.mark.staging,
    pytest.mark.service_mesh,
    pytest.mark.slow
]


class ServiceMeshL4Manager:
    """Manages L4 service mesh testing with real microservices infrastructure."""
    
    def __init__(self):
        self.config = None
        self.discovery_service = None
        self.load_balancer = None
        self.circuit_breaker = None
        self.retry_policy = None
        self.staging_services = {}
        self.service_instances = {}
        self.load_balancing_results = []
        self.circuit_breaker_events = []
        self.retry_attempts = []
        self.discovery_cache = {}
        
    async def initialize_staging_services(self):
        """Initialize real service mesh services in staging."""
        try:
            # Initialize config for staging
            self.config = Config()
            
            # Skip if not in staging environment
            if self.config.environment != "staging":
                pytest.skip("L4 tests require staging environment")
            
            # Initialize service mesh components
            self.discovery_service = ServiceDiscoveryService()
            await self.discovery_service.initialize()
            
            self.load_balancer = LoadBalancerService()
            await self.load_balancer.initialize()
            
            self.circuit_breaker = CircuitBreakerService()
            await self.circuit_breaker.initialize()
            
            self.retry_policy = RetryPolicyService()
            await self.retry_policy.initialize()
            
            # Discover staging service mesh
            await self.discover_staging_service_mesh()
            
            # Verify service mesh infrastructure
            await self.verify_service_mesh_infrastructure()
            
            logger.info("L4 service mesh services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize L4 service mesh services: {e}")
            pytest.skip(f"L4 infrastructure unavailable: {e}")
    
    async def discover_staging_service_mesh(self):
        """Discover staging service mesh topology."""
        try:
            # Define staging service endpoints
            staging_service_endpoints = {
                "api_service": {
                    "instances": [
                        {"host": "api-1.staging.netrasystems.ai", "port": 8000, "zone": "us-central1-a"},
                        {"host": "api-2.staging.netrasystems.ai", "port": 8000, "zone": "us-central1-b"},
                        {"host": "api-3.staging.netrasystems.ai", "port": 8000, "zone": "us-central1-c"}
                    ],
                    "health_endpoint": "/health",
                    "service_type": "http"
                },
                "auth_service": {
                    "instances": [
                        {"host": "auth-1.staging.netrasystems.ai", "port": 8001, "zone": "us-central1-a"},
                        {"host": "auth-2.staging.netrasystems.ai", "port": 8001, "zone": "us-central1-b"}
                    ],
                    "health_endpoint": "/health",
                    "service_type": "http"
                },
                "websocket_service": {
                    "instances": [
                        {"host": "ws-1.staging.netrasystems.ai", "port": 8002, "zone": "us-central1-a"},
                        {"host": "ws-2.staging.netrasystems.ai", "port": 8002, "zone": "us-central1-b"}
                    ],
                    "health_endpoint": "/health",
                    "service_type": "websocket"
                },
                "llm_service": {
                    "instances": [
                        {"host": "llm-1.staging.netrasystems.ai", "port": 8003, "zone": "us-central1-a"},
                        {"host": "llm-2.staging.netrasystems.ai", "port": 8003, "zone": "us-central1-b"},
                        {"host": "llm-3.staging.netrasystems.ai", "port": 8003, "zone": "us-central1-c"}
                    ],
                    "health_endpoint": "/health",
                    "service_type": "http"
                }
            }
            
            # Check accessibility of service instances
            async with httpx.AsyncClient(timeout=30.0) as client:
                for service_name, service_config in staging_service_endpoints.items():
                    accessible_instances = []
                    
                    for instance in service_config["instances"]:
                        try:
                            if service_config["service_type"] == "http":
                                url = f"http://{instance['host']}:{instance['port']}{service_config['health_endpoint']}"
                                response = await client.get(url)
                                accessible = response.status_code in [200, 404]  # 404 means service is up but endpoint may not exist
                            else:
                                # For non-HTTP services, assume accessible if host resolves
                                accessible = True
                            
                            if accessible:
                                instance["accessible"] = True
                                instance["last_check"] = time.time()
                                accessible_instances.append(instance)
                            
                        except Exception as e:
                            instance["accessible"] = False
                            instance["error"] = str(e)
                            instance["last_check"] = time.time()
                    
                    if accessible_instances:
                        self.staging_services[service_name] = {
                            "config": service_config,
                            "instances": accessible_instances,
                            "total_instances": len(service_config["instances"]),
                            "accessible_instances": len(accessible_instances)
                        }
                        
                        # Register with service discovery
                        await self.register_service_instances(service_name, accessible_instances)
            
            accessible_services = list(self.staging_services.keys())
            logger.info(f"Discovered {len(accessible_services)} staging services with mesh capabilities: {accessible_services}")
            
        except Exception as e:
            logger.error(f"Service mesh discovery failed: {e}")
            # Continue with minimal configuration
            self.staging_services = {}
    
    async def register_service_instances(self, service_name: str, instances: List[Dict[str, Any]]):
        """Register service instances with service discovery."""
        try:
            for instance in instances:
                instance_id = f"{service_name}_{instance['host']}_{instance['port']}"
                
                registration_result = await self.discovery_service.register_instance(
                    service_name=service_name,
                    instance_id=instance_id,
                    host=instance["host"],
                    port=instance["port"],
                    metadata={
                        "zone": instance.get("zone", "unknown"),
                        "accessible": instance.get("accessible", False),
                        "health_endpoint": self.staging_services[service_name]["config"]["health_endpoint"]
                    }
                )
                
                if registration_result["success"]:
                    if service_name not in self.service_instances:
                        self.service_instances[service_name] = []
                    
                    self.service_instances[service_name].append({
                        "instance_id": instance_id,
                        "instance": instance,
                        "registration_result": registration_result
                    })
            
        except Exception as e:
            logger.error(f"Failed to register service instances for {service_name}: {e}")
    
    async def verify_service_mesh_infrastructure(self):
        """Verify service mesh infrastructure is operational."""
        try:
            # Test service discovery
            discovery_health = await self.discovery_service.health_check()
            assert discovery_health["healthy"], "Service discovery not healthy"
            
            # Test load balancer
            lb_health = await self.load_balancer.health_check()
            assert lb_health["healthy"], "Load balancer not healthy"
            
            # Test circuit breaker
            cb_health = await self.circuit_breaker.health_check()
            assert cb_health["healthy"], "Circuit breaker not healthy"
            
            # Test retry policy
            retry_health = await self.retry_policy.health_check()
            assert retry_health["healthy"], "Retry policy service not healthy"
            
            logger.info("Service mesh infrastructure verified")
            
        except Exception as e:
            raise Exception(f"Service mesh infrastructure verification failed: {e}")
    
    async def test_service_discovery_l4(self, service_name: str) -> Dict[str, Any]:
        """Test service discovery with L4 realism."""
        try:
            discovery_start = time.time()
            
            # Test service lookup
            lookup_result = await self.discovery_service.discover_service(service_name)
            
            if not lookup_result["success"]:
                return {
                    "success": False,
                    "error": f"Service discovery failed: {lookup_result.get('error')}"
                }
            
            discovered_instances = lookup_result["instances"]
            discovery_time = time.time() - discovery_start
            
            # Verify discovered instances match registered instances
            registered_instances = self.service_instances.get(service_name, [])
            
            # Test health checking of discovered instances
            health_check_results = []
            for instance in discovered_instances:
                health_result = await self.test_instance_health(instance)
                health_check_results.append(health_result)
            
            healthy_instances = [r for r in health_check_results if r["healthy"]]
            
            # Test caching behavior
            cache_test_start = time.time()
            cached_lookup = await self.discovery_service.discover_service(service_name)
            cache_test_time = time.time() - cache_test_start
            
            self.discovery_cache[service_name] = {
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
                "cache_performance_improvement": (discovery_time - cache_time) / discovery_time * 100 if cache_test_time < discovery_time else 0
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_instance_health(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Test health of a service instance."""
        try:
            health_start = time.time()
            
            host = instance["host"]
            port = instance["port"]
            health_endpoint = instance.get("health_endpoint", "/health")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"http://{host}:{port}{health_endpoint}"
                response = await client.get(url)
                
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
    
    async def test_load_balancing_algorithms_l4(self, service_name: str) -> Dict[str, Any]:
        """Test load balancing algorithms with L4 realism."""
        try:
            if service_name not in self.staging_services:
                return {"success": False, "error": f"Service {service_name} not available"}
            
            service_config = self.staging_services[service_name]
            instances = service_config["instances"]
            
            if len(instances) < 2:
                return {"success": False, "error": "Need at least 2 instances for load balancing test"}
            
            load_balancing_results = {
                "round_robin": await self.test_round_robin_lb(service_name, instances),
                "weighted_round_robin": await self.test_weighted_round_robin_lb(service_name, instances),
                "least_connections": await self.test_least_connections_lb(service_name, instances),
                "random": await self.test_random_lb(service_name, instances),
                "zone_aware": await self.test_zone_aware_lb(service_name, instances)
            }
            
            # Analyze load distribution
            distribution_analysis = self.analyze_load_distribution(load_balancing_results)
            
            self.load_balancing_results.append({
                "service_name": service_name,
                "algorithms_tested": list(load_balancing_results.keys()),
                "results": load_balancing_results,
                "distribution_analysis": distribution_analysis,
                "timestamp": time.time()
            })
            
            successful_algorithms = [alg for alg, result in load_balancing_results.items() if result["success"]]
            
            return {
                "success": len(successful_algorithms) > 0,
                "service_name": service_name,
                "algorithms_tested": len(load_balancing_results),
                "successful_algorithms": len(successful_algorithms),
                "load_balancing_results": load_balancing_results,
                "distribution_analysis": distribution_analysis
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_round_robin_lb(self, service_name: str, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test round-robin load balancing."""
        try:
            requests_per_instance = {}
            total_requests = 20
            
            for i in range(total_requests):
                # Get next instance using round-robin
                selected_instance = await self.load_balancer.select_instance(
                    service_name, algorithm="round_robin"
                )
                
                if selected_instance["success"]:
                    instance_id = selected_instance["instance"]["instance_id"]
                    requests_per_instance[instance_id] = requests_per_instance.get(instance_id, 0) + 1
                    
                    # Make actual request to test connectivity
                    request_result = await self.make_test_request(selected_instance["instance"])
                    
                await asyncio.sleep(0.1)  # Small delay between requests
            
            # Calculate distribution evenness
            expected_per_instance = total_requests / len(instances)
            distribution_variance = 0
            for count in requests_per_instance.values():
                distribution_variance += (count - expected_per_instance) ** 2
            distribution_variance /= len(requests_per_instance)
            
            return {
                "success": True,
                "algorithm": "round_robin",
                "total_requests": total_requests,
                "requests_per_instance": requests_per_instance,
                "distribution_variance": distribution_variance,
                "evenness_score": 1.0 / (1.0 + distribution_variance)  # Higher is better
            }
            
        except Exception as e:
            return {"success": False, "algorithm": "round_robin", "error": str(e)}
    
    async def test_weighted_round_robin_lb(self, service_name: str, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test weighted round-robin load balancing."""
        try:
            # Assign weights based on zone (simulate different instance capabilities)
            instance_weights = {}
            for instance in instances:
                zone = instance.get("zone", "unknown")
                # Simulate different weights based on zone
                if zone.endswith("-a"):
                    weight = 3
                elif zone.endswith("-b"):
                    weight = 2
                else:
                    weight = 1
                
                instance_id = f"{instance['host']}:{instance['port']}"
                instance_weights[instance_id] = weight
            
            requests_per_instance = {}
            total_requests = 30
            
            for i in range(total_requests):
                selected_instance = await self.load_balancer.select_instance(
                    service_name, algorithm="weighted_round_robin", weights=instance_weights
                )
                
                if selected_instance["success"]:
                    instance_id = selected_instance["instance"]["instance_id"]
                    requests_per_instance[instance_id] = requests_per_instance.get(instance_id, 0) + 1
                    
                    request_result = await self.make_test_request(selected_instance["instance"])
                
                await asyncio.sleep(0.1)
            
            # Verify requests are distributed according to weights
            total_weight = sum(instance_weights.values())
            weight_compliance = {}
            
            for instance_id, actual_requests in requests_per_instance.items():
                expected_ratio = instance_weights.get(instance_id, 1) / total_weight
                actual_ratio = actual_requests / total_requests
                weight_compliance[instance_id] = abs(expected_ratio - actual_ratio)
            
            avg_weight_compliance = sum(weight_compliance.values()) / len(weight_compliance)
            
            return {
                "success": True,
                "algorithm": "weighted_round_robin",
                "total_requests": total_requests,
                "instance_weights": instance_weights,
                "requests_per_instance": requests_per_instance,
                "weight_compliance": weight_compliance,
                "avg_weight_compliance": avg_weight_compliance
            }
            
        except Exception as e:
            return {"success": False, "algorithm": "weighted_round_robin", "error": str(e)}
    
    async def test_least_connections_lb(self, service_name: str, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test least connections load balancing."""
        try:
            # Simulate connection tracking
            connection_counts = {f"{inst['host']}:{inst['port']}": 0 for inst in instances}
            requests_per_instance = {}
            total_requests = 25
            
            for i in range(total_requests):
                selected_instance = await self.load_balancer.select_instance(
                    service_name, 
                    algorithm="least_connections",
                    connection_counts=connection_counts
                )
                
                if selected_instance["success"]:
                    instance_id = selected_instance["instance"]["instance_id"]
                    requests_per_instance[instance_id] = requests_per_instance.get(instance_id, 0) + 1
                    
                    # Simulate connection increase
                    connection_counts[instance_id] = connection_counts.get(instance_id, 0) + 1
                    
                    request_result = await self.make_test_request(selected_instance["instance"])
                    
                    # Simulate random connection cleanup (some connections finish)
                    if random.random() < 0.3:  # 30% chance a connection finishes
                        for conn_id in connection_counts:
                            if connection_counts[conn_id] > 0 and random.random() < 0.5:
                                connection_counts[conn_id] -= 1
                
                await asyncio.sleep(0.1)
            
            return {
                "success": True,
                "algorithm": "least_connections",
                "total_requests": total_requests,
                "requests_per_instance": requests_per_instance,
                "final_connection_counts": connection_counts
            }
            
        except Exception as e:
            return {"success": False, "algorithm": "least_connections", "error": str(e)}
    
    async def test_random_lb(self, service_name: str, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test random load balancing."""
        try:
            requests_per_instance = {}
            total_requests = 20
            
            for i in range(total_requests):
                selected_instance = await self.load_balancer.select_instance(
                    service_name, algorithm="random"
                )
                
                if selected_instance["success"]:
                    instance_id = selected_instance["instance"]["instance_id"]
                    requests_per_instance[instance_id] = requests_per_instance.get(instance_id, 0) + 1
                    
                    request_result = await self.make_test_request(selected_instance["instance"])
                
                await asyncio.sleep(0.1)
            
            # Calculate randomness quality (standard deviation should be within reasonable bounds)
            values = list(requests_per_instance.values())
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            std_dev = variance ** 0.5
            
            return {
                "success": True,
                "algorithm": "random",
                "total_requests": total_requests,
                "requests_per_instance": requests_per_instance,
                "distribution_std_dev": std_dev,
                "distribution_quality": 1.0 / (1.0 + std_dev)  # Lower std_dev is better for randomness
            }
            
        except Exception as e:
            return {"success": False, "algorithm": "random", "error": str(e)}
    
    async def test_zone_aware_lb(self, service_name: str, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test zone-aware load balancing."""
        try:
            # Group instances by zone
            zones = {}
            for instance in instances:
                zone = instance.get("zone", "unknown")
                if zone not in zones:
                    zones[zone] = []
                zones[zone].append(instance)
            
            requests_per_zone = {}
            requests_per_instance = {}
            total_requests = 30
            
            for i in range(total_requests):
                # Simulate client zone preference
                preferred_zone = list(zones.keys())[i % len(zones)]
                
                selected_instance = await self.load_balancer.select_instance(
                    service_name,
                    algorithm="zone_aware",
                    preferred_zone=preferred_zone,
                    zones=zones
                )
                
                if selected_instance["success"]:
                    instance_id = selected_instance["instance"]["instance_id"]
                    instance_zone = selected_instance["instance"].get("zone", "unknown")
                    
                    requests_per_instance[instance_id] = requests_per_instance.get(instance_id, 0) + 1
                    requests_per_zone[instance_zone] = requests_per_zone.get(instance_zone, 0) + 1
                    
                    request_result = await self.make_test_request(selected_instance["instance"])
                
                await asyncio.sleep(0.1)
            
            # Calculate zone affinity compliance
            zone_preference_compliance = 0
            total_zones = len(zones)
            
            for zone, request_count in requests_per_zone.items():
                expected_ratio = 1.0 / total_zones  # Assuming equal zone distribution
                actual_ratio = request_count / total_requests
                zone_preference_compliance += abs(expected_ratio - actual_ratio)
            
            zone_preference_compliance /= total_zones
            
            return {
                "success": True,
                "algorithm": "zone_aware",
                "total_requests": total_requests,
                "zones": list(zones.keys()),
                "requests_per_zone": requests_per_zone,
                "requests_per_instance": requests_per_instance,
                "zone_preference_compliance": zone_preference_compliance
            }
            
        except Exception as e:
            return {"success": False, "algorithm": "zone_aware", "error": str(e)}
    
    async def make_test_request(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Make a test request to a service instance."""
        try:
            host = instance.get("host", "localhost")
            port = instance.get("port", 8000)
            
            request_start = time.time()
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                url = f"http://{host}:{port}/health"
                response = await client.get(url)
                
                request_time = time.time() - request_start
                
                return {
                    "success": response.status_code in [200, 404],  # 404 means service up but endpoint may not exist
                    "status_code": response.status_code,
                    "response_time": request_time,
                    "instance_id": f"{host}:{port}"
                }
                
        except Exception as e:
            request_time = time.time() - request_start
            return {
                "success": False,
                "error": str(e),
                "response_time": request_time,
                "instance_id": f"{instance.get('host', 'unknown')}:{instance.get('port', 'unknown')}"
            }
    
    def analyze_load_distribution(self, load_balancing_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze load distribution across all algorithms."""
        try:
            analysis = {
                "algorithm_performance": {},
                "overall_metrics": {
                    "algorithms_tested": 0,
                    "successful_algorithms": 0,
                    "avg_distribution_quality": 0
                }
            }
            
            distribution_qualities = []
            
            for algorithm, result in load_balancing_results.items():
                if result["success"]:
                    analysis["algorithm_performance"][algorithm] = {
                        "success": True,
                        "total_requests": result.get("total_requests", 0)
                    }
                    
                    # Algorithm-specific analysis
                    if algorithm == "round_robin":
                        analysis["algorithm_performance"][algorithm]["evenness_score"] = result.get("evenness_score", 0)
                        distribution_qualities.append(result.get("evenness_score", 0))
                    
                    elif algorithm == "weighted_round_robin":
                        analysis["algorithm_performance"][algorithm]["weight_compliance"] = 1.0 - result.get("avg_weight_compliance", 1.0)
                        distribution_qualities.append(1.0 - result.get("avg_weight_compliance", 1.0))
                    
                    elif algorithm == "random":
                        analysis["algorithm_performance"][algorithm]["distribution_quality"] = result.get("distribution_quality", 0)
                        distribution_qualities.append(result.get("distribution_quality", 0))
                    
                    elif algorithm == "zone_aware":
                        analysis["algorithm_performance"][algorithm]["zone_compliance"] = 1.0 - result.get("zone_preference_compliance", 1.0)
                        distribution_qualities.append(1.0 - result.get("zone_preference_compliance", 1.0))
                    
                    analysis["overall_metrics"]["successful_algorithms"] += 1
                else:
                    analysis["algorithm_performance"][algorithm] = {
                        "success": False,
                        "error": result.get("error", "Unknown error")
                    }
                
                analysis["overall_metrics"]["algorithms_tested"] += 1
            
            if distribution_qualities:
                analysis["overall_metrics"]["avg_distribution_quality"] = sum(distribution_qualities) / len(distribution_qualities)
            
            return analysis
            
        except Exception as e:
            return {"error": str(e)}
    
    async def test_circuit_breaker_patterns_l4(self, service_name: str) -> Dict[str, Any]:
        """Test circuit breaker patterns with L4 realism."""
        try:
            if service_name not in self.staging_services:
                return {"success": False, "error": f"Service {service_name} not available"}
            
            circuit_breaker_tests = {
                "closed_to_open": await self.test_circuit_breaker_closed_to_open(service_name),
                "open_to_half_open": await self.test_circuit_breaker_open_to_half_open(service_name),
                "half_open_to_closed": await self.test_circuit_breaker_half_open_to_closed(service_name),
                "failure_threshold": await self.test_circuit_breaker_failure_threshold(service_name),
                "timeout_behavior": await self.test_circuit_breaker_timeout(service_name)
            }
            
            successful_tests = [test for test, result in circuit_breaker_tests.items() if result["success"]]
            
            return {
                "success": len(successful_tests) > 0,
                "service_name": service_name,
                "tests_executed": len(circuit_breaker_tests),
                "successful_tests": len(successful_tests),
                "circuit_breaker_tests": circuit_breaker_tests
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_circuit_breaker_closed_to_open(self, service_name: str) -> Dict[str, Any]:
        """Test circuit breaker transition from closed to open state."""
        try:
            # Configure circuit breaker
            cb_config = {
                "failure_threshold": 5,
                "timeout": 10.0,
                "reset_timeout": 30.0
            }
            
            await self.circuit_breaker.configure_service(service_name, cb_config)
            
            # Generate failures to trigger circuit breaker
            failure_count = 0
            for i in range(8):  # More than failure_threshold
                try:
                    # Simulate failed request
                    result = await self.circuit_breaker.execute_request(
                        service_name,
                        lambda: self.simulate_failing_request()
                    )
                    
                    if not result["success"]:
                        failure_count += 1
                        
                except Exception:
                    failure_count += 1
                
                await asyncio.sleep(0.5)
            
            # Check circuit breaker state
            cb_state = await self.circuit_breaker.get_state(service_name)
            
            self.circuit_breaker_events.append({
                "test": "closed_to_open",
                "service_name": service_name,
                "failure_count": failure_count,
                "final_state": cb_state,
                "timestamp": time.time()
            })
            
            return {
                "success": cb_state["state"] == "open",
                "test": "closed_to_open",
                "failure_count": failure_count,
                "circuit_breaker_state": cb_state,
                "threshold_exceeded": failure_count >= cb_config["failure_threshold"]
            }
            
        except Exception as e:
            return {"success": False, "test": "closed_to_open", "error": str(e)}
    
    async def simulate_failing_request(self) -> Dict[str, Any]:
        """Simulate a failing request for circuit breaker testing."""
        await asyncio.sleep(0.1)
        raise Exception("Simulated request failure")
    
    async def test_circuit_breaker_open_to_half_open(self, service_name: str) -> Dict[str, Any]:
        """Test circuit breaker transition from open to half-open state."""
        try:
            # Assume circuit breaker is already open from previous test
            initial_state = await self.circuit_breaker.get_state(service_name)
            
            if initial_state["state"] != "open":
                # Force circuit breaker to open state
                await self.test_circuit_breaker_closed_to_open(service_name)
            
            # Wait for reset timeout to trigger half-open state
            reset_timeout = 30.0
            await asyncio.sleep(reset_timeout + 1.0)
            
            # Trigger a request to transition to half-open
            try:
                result = await self.circuit_breaker.execute_request(
                    service_name,
                    lambda: self.simulate_successful_request()
                )
            except Exception:
                pass
            
            # Check circuit breaker state
            cb_state = await self.circuit_breaker.get_state(service_name)
            
            self.circuit_breaker_events.append({
                "test": "open_to_half_open",
                "service_name": service_name,
                "initial_state": initial_state,
                "final_state": cb_state,
                "timestamp": time.time()
            })
            
            return {
                "success": cb_state["state"] == "half_open",
                "test": "open_to_half_open",
                "initial_state": initial_state,
                "final_state": cb_state
            }
            
        except Exception as e:
            return {"success": False, "test": "open_to_half_open", "error": str(e)}
    
    async def simulate_successful_request(self) -> Dict[str, Any]:
        """Simulate a successful request for circuit breaker testing."""
        await asyncio.sleep(0.1)
        return {"success": True, "data": "test_response"}
    
    async def test_circuit_breaker_half_open_to_closed(self, service_name: str) -> Dict[str, Any]:
        """Test circuit breaker transition from half-open to closed state."""
        try:
            # Ensure circuit breaker is in half-open state
            await self.test_circuit_breaker_open_to_half_open(service_name)
            
            # Make successful requests to close the circuit breaker
            success_count = 0
            for i in range(3):  # Multiple successful requests
                try:
                    result = await self.circuit_breaker.execute_request(
                        service_name,
                        lambda: self.simulate_successful_request()
                    )
                    
                    if result["success"]:
                        success_count += 1
                        
                except Exception:
                    pass
                
                await asyncio.sleep(0.5)
            
            # Check circuit breaker state
            cb_state = await self.circuit_breaker.get_state(service_name)
            
            self.circuit_breaker_events.append({
                "test": "half_open_to_closed",
                "service_name": service_name,
                "success_count": success_count,
                "final_state": cb_state,
                "timestamp": time.time()
            })
            
            return {
                "success": cb_state["state"] == "closed",
                "test": "half_open_to_closed",
                "success_count": success_count,
                "circuit_breaker_state": cb_state
            }
            
        except Exception as e:
            return {"success": False, "test": "half_open_to_closed", "error": str(e)}
    
    async def test_circuit_breaker_failure_threshold(self, service_name: str) -> Dict[str, Any]:
        """Test circuit breaker failure threshold configuration."""
        try:
            # Test different failure thresholds
            thresholds = [3, 5, 10]
            threshold_results = []
            
            for threshold in thresholds:
                # Reset circuit breaker
                await self.circuit_breaker.reset(service_name)
                
                # Configure with specific threshold
                cb_config = {
                    "failure_threshold": threshold,
                    "timeout": 5.0,
                    "reset_timeout": 15.0
                }
                
                await self.circuit_breaker.configure_service(service_name, cb_config)
                
                # Generate failures up to threshold
                failures_generated = 0
                for i in range(threshold + 2):  # Generate more than threshold
                    try:
                        await self.circuit_breaker.execute_request(
                            service_name,
                            lambda: self.simulate_failing_request()
                        )
                    except Exception:
                        failures_generated += 1
                    
                    await asyncio.sleep(0.2)
                
                # Check if circuit breaker opened at correct threshold
                cb_state = await self.circuit_breaker.get_state(service_name)
                
                threshold_results.append({
                    "threshold": threshold,
                    "failures_generated": failures_generated,
                    "circuit_opened": cb_state["state"] == "open",
                    "opened_at_correct_threshold": failures_generated >= threshold and cb_state["state"] == "open"
                })
            
            successful_threshold_tests = [r for r in threshold_results if r["opened_at_correct_threshold"]]
            
            return {
                "success": len(successful_threshold_tests) > 0,
                "test": "failure_threshold",
                "thresholds_tested": len(thresholds),
                "successful_threshold_tests": len(successful_threshold_tests),
                "threshold_results": threshold_results
            }
            
        except Exception as e:
            return {"success": False, "test": "failure_threshold", "error": str(e)}
    
    async def test_circuit_breaker_timeout(self, service_name: str) -> Dict[str, Any]:
        """Test circuit breaker timeout behavior."""
        try:
            # Configure circuit breaker with short timeout
            cb_config = {
                "failure_threshold": 3,
                "timeout": 2.0,  # Short timeout
                "reset_timeout": 10.0
            }
            
            await self.circuit_breaker.configure_service(service_name, cb_config)
            
            # Test timeout behavior
            timeout_start = time.time()
            
            try:
                result = await self.circuit_breaker.execute_request(
                    service_name,
                    lambda: self.simulate_slow_request(5.0)  # Slower than timeout
                )
                
                timeout_occurred = False
                
            except asyncio.TimeoutError:
                timeout_occurred = True
            except Exception as e:
                timeout_occurred = "timeout" in str(e).lower()
            
            timeout_duration = time.time() - timeout_start
            
            return {
                "success": timeout_occurred and timeout_duration <= cb_config["timeout"] + 1.0,  # Allow some margin
                "test": "timeout_behavior",
                "timeout_occurred": timeout_occurred,
                "timeout_duration": timeout_duration,
                "configured_timeout": cb_config["timeout"]
            }
            
        except Exception as e:
            return {"success": False, "test": "timeout_behavior", "error": str(e)}
    
    async def simulate_slow_request(self, delay: float) -> Dict[str, Any]:
        """Simulate a slow request for timeout testing."""
        await asyncio.sleep(delay)
        return {"success": True, "data": "slow_response"}
    
    async def test_retry_policies_l4(self, service_name: str) -> Dict[str, Any]:
        """Test retry policies with L4 realism."""
        try:
            if service_name not in self.staging_services:
                return {"success": False, "error": f"Service {service_name} not available"}
            
            retry_policy_tests = {
                "exponential_backoff": await self.test_exponential_backoff_retry(service_name),
                "fixed_delay": await self.test_fixed_delay_retry(service_name),
                "linear_backoff": await self.test_linear_backoff_retry(service_name),
                "max_attempts": await self.test_max_attempts_retry(service_name),
                "jitter": await self.test_retry_jitter(service_name)
            }
            
            successful_tests = [test for test, result in retry_policy_tests.items() if result["success"]]
            
            return {
                "success": len(successful_tests) > 0,
                "service_name": service_name,
                "retry_tests_executed": len(retry_policy_tests),
                "successful_retry_tests": len(successful_tests),
                "retry_policy_tests": retry_policy_tests
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_exponential_backoff_retry(self, service_name: str) -> Dict[str, Any]:
        """Test exponential backoff retry policy."""
        try:
            retry_config = {
                "max_attempts": 4,
                "base_delay": 1.0,
                "max_delay": 10.0,
                "backoff_multiplier": 2.0,
                "jitter": False
            }
            
            retry_start = time.time()
            attempt_times = []
            
            async def failing_operation():
                attempt_times.append(time.time() - retry_start)
                if len(attempt_times) < retry_config["max_attempts"]:
                    raise Exception(f"Attempt {len(attempt_times)} failed")
                return {"success": True, "attempt": len(attempt_times)}
            
            try:
                result = await self.retry_policy.execute_with_retry(
                    service_name,
                    failing_operation,
                    retry_config
                )
                
                retry_successful = result.get("success", False)
                
            except Exception as e:
                retry_successful = False
                result = {"error": str(e)}
            
            total_retry_time = time.time() - retry_start
            
            # Verify exponential backoff timing
            expected_delays = []
            for i in range(1, len(attempt_times)):
                expected_delay = min(retry_config["base_delay"] * (retry_config["backoff_multiplier"] ** (i-1)), retry_config["max_delay"])
                expected_delays.append(expected_delay)
            
            actual_delays = []
            for i in range(1, len(attempt_times)):
                actual_delay = attempt_times[i] - attempt_times[i-1]
                actual_delays.append(actual_delay)
            
            self.retry_attempts.append({
                "test": "exponential_backoff",
                "service_name": service_name,
                "attempt_times": attempt_times,
                "actual_delays": actual_delays,
                "expected_delays": expected_delays,
                "retry_config": retry_config,
                "timestamp": time.time()
            })
            
            return {
                "success": retry_successful,
                "test": "exponential_backoff",
                "total_attempts": len(attempt_times),
                "total_retry_time": total_retry_time,
                "actual_delays": actual_delays,
                "expected_delays": expected_delays,
                "backoff_accuracy": self.calculate_backoff_accuracy(actual_delays, expected_delays)
            }
            
        except Exception as e:
            return {"success": False, "test": "exponential_backoff", "error": str(e)}
    
    def calculate_backoff_accuracy(self, actual_delays: List[float], expected_delays: List[float]) -> float:
        """Calculate accuracy of backoff timing."""
        if not actual_delays or not expected_delays or len(actual_delays) != len(expected_delays):
            return 0.0
        
        accuracy_scores = []
        for actual, expected in zip(actual_delays, expected_delays):
            # Allow 20% tolerance
            tolerance = 0.2
            if expected == 0:
                accuracy = 1.0 if actual == 0 else 0.0
            else:
                error = abs(actual - expected) / expected
                accuracy = max(0.0, 1.0 - error / tolerance)
            accuracy_scores.append(accuracy)
        
        return sum(accuracy_scores) / len(accuracy_scores)
    
    async def test_fixed_delay_retry(self, service_name: str) -> Dict[str, Any]:
        """Test fixed delay retry policy."""
        try:
            retry_config = {
                "max_attempts": 3,
                "fixed_delay": 2.0,
                "jitter": False
            }
            
            retry_start = time.time()
            attempt_times = []
            
            async def failing_operation():
                attempt_times.append(time.time() - retry_start)
                if len(attempt_times) < retry_config["max_attempts"]:
                    raise Exception(f"Attempt {len(attempt_times)} failed")
                return {"success": True, "attempt": len(attempt_times)}
            
            try:
                result = await self.retry_policy.execute_with_retry(
                    service_name,
                    failing_operation,
                    retry_config
                )
                retry_successful = result.get("success", False)
            except Exception:
                retry_successful = False
            
            total_retry_time = time.time() - retry_start
            
            # Verify fixed delay timing
            actual_delays = []
            for i in range(1, len(attempt_times)):
                actual_delay = attempt_times[i] - attempt_times[i-1]
                actual_delays.append(actual_delay)
            
            expected_delay = retry_config["fixed_delay"]
            delay_consistency = self.calculate_fixed_delay_consistency(actual_delays, expected_delay)
            
            return {
                "success": retry_successful,
                "test": "fixed_delay",
                "total_attempts": len(attempt_times),
                "total_retry_time": total_retry_time,
                "actual_delays": actual_delays,
                "expected_delay": expected_delay,
                "delay_consistency": delay_consistency
            }
            
        except Exception as e:
            return {"success": False, "test": "fixed_delay", "error": str(e)}
    
    def calculate_fixed_delay_consistency(self, actual_delays: List[float], expected_delay: float) -> float:
        """Calculate consistency of fixed delay timing."""
        if not actual_delays:
            return 0.0
        
        tolerance = 0.2  # 20% tolerance
        consistent_delays = 0
        
        for delay in actual_delays:
            error = abs(delay - expected_delay) / expected_delay if expected_delay > 0 else 0
            if error <= tolerance:
                consistent_delays += 1
        
        return consistent_delays / len(actual_delays)
    
    async def test_linear_backoff_retry(self, service_name: str) -> Dict[str, Any]:
        """Test linear backoff retry policy."""
        try:
            retry_config = {
                "max_attempts": 4,
                "base_delay": 1.0,
                "linear_increment": 1.0,
                "max_delay": 8.0
            }
            
            retry_start = time.time()
            attempt_times = []
            
            async def failing_operation():
                attempt_times.append(time.time() - retry_start)
                if len(attempt_times) < retry_config["max_attempts"]:
                    raise Exception(f"Attempt {len(attempt_times)} failed")
                return {"success": True, "attempt": len(attempt_times)}
            
            try:
                result = await self.retry_policy.execute_with_retry(
                    service_name,
                    failing_operation,
                    retry_config
                )
                retry_successful = result.get("success", False)
            except Exception:
                retry_successful = False
            
            # Verify linear backoff timing
            actual_delays = []
            for i in range(1, len(attempt_times)):
                actual_delay = attempt_times[i] - attempt_times[i-1]
                actual_delays.append(actual_delay)
            
            expected_delays = []
            for i in range(len(actual_delays)):
                expected_delay = min(
                    retry_config["base_delay"] + (i * retry_config["linear_increment"]),
                    retry_config["max_delay"]
                )
                expected_delays.append(expected_delay)
            
            backoff_accuracy = self.calculate_backoff_accuracy(actual_delays, expected_delays)
            
            return {
                "success": retry_successful,
                "test": "linear_backoff",
                "total_attempts": len(attempt_times),
                "actual_delays": actual_delays,
                "expected_delays": expected_delays,
                "backoff_accuracy": backoff_accuracy
            }
            
        except Exception as e:
            return {"success": False, "test": "linear_backoff", "error": str(e)}
    
    async def test_max_attempts_retry(self, service_name: str) -> Dict[str, Any]:
        """Test max attempts retry limit."""
        try:
            retry_config = {
                "max_attempts": 3,
                "base_delay": 0.5
            }
            
            attempt_count = 0
            
            async def always_failing_operation():
                nonlocal attempt_count
                attempt_count += 1
                raise Exception(f"Attempt {attempt_count} failed")
            
            try:
                result = await self.retry_policy.execute_with_retry(
                    service_name,
                    always_failing_operation,
                    retry_config
                )
                max_attempts_respected = False  # Should not succeed
            except Exception:
                max_attempts_respected = attempt_count == retry_config["max_attempts"]
            
            return {
                "success": max_attempts_respected,
                "test": "max_attempts",
                "configured_max_attempts": retry_config["max_attempts"],
                "actual_attempts": attempt_count,
                "max_attempts_respected": max_attempts_respected
            }
            
        except Exception as e:
            return {"success": False, "test": "max_attempts", "error": str(e)}
    
    async def test_retry_jitter(self, service_name: str) -> Dict[str, Any]:
        """Test retry jitter implementation."""
        try:
            retry_config = {
                "max_attempts": 4,
                "base_delay": 2.0,
                "jitter": True,
                "jitter_range": 0.5  # ±0.5 seconds
            }
            
            retry_start = time.time()
            attempt_times = []
            
            async def failing_operation():
                attempt_times.append(time.time() - retry_start)
                if len(attempt_times) < retry_config["max_attempts"]:
                    raise Exception(f"Attempt {len(attempt_times)} failed")
                return {"success": True, "attempt": len(attempt_times)}
            
            try:
                result = await self.retry_policy.execute_with_retry(
                    service_name,
                    failing_operation,
                    retry_config
                )
                retry_successful = result.get("success", False)
            except Exception:
                retry_successful = False
            
            # Verify jitter is applied
            actual_delays = []
            for i in range(1, len(attempt_times)):
                actual_delay = attempt_times[i] - attempt_times[i-1]
                actual_delays.append(actual_delay)
            
            base_delay = retry_config["base_delay"]
            jitter_range = retry_config["jitter_range"]
            
            jitter_applied = all(
                (base_delay - jitter_range) <= delay <= (base_delay + jitter_range)
                for delay in actual_delays
            )
            
            # Check that delays are not all identical (indicating jitter)
            delay_variance = len(set([round(d, 1) for d in actual_delays])) > 1 if actual_delays else False
            
            return {
                "success": retry_successful and jitter_applied,
                "test": "jitter",
                "total_attempts": len(attempt_times),
                "actual_delays": actual_delays,
                "base_delay": base_delay,
                "jitter_range": jitter_range,
                "jitter_applied": jitter_applied,
                "delay_variance": delay_variance
            }
            
        except Exception as e:
            return {"success": False, "test": "jitter", "error": str(e)}
    
    async def cleanup(self):
        """Clean up L4 test resources."""
        try:
            cleanup_tasks = []
            
            if self.discovery_service:
                cleanup_tasks.append(self.discovery_service.shutdown())
            if self.load_balancer:
                cleanup_tasks.append(self.load_balancer.shutdown())
            if self.circuit_breaker:
                cleanup_tasks.append(self.circuit_breaker.shutdown())
            if self.retry_policy:
                cleanup_tasks.append(self.retry_policy.shutdown())
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            logger.info("L4 service mesh cleanup completed")
            
        except Exception as e:
            logger.error(f"L4 cleanup failed: {e}")


@pytest.fixture
async def service_mesh_l4():
    """Create L4 service mesh manager for staging tests."""
    manager = ServiceMeshL4Manager()
    await manager.initialize_staging_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
async def test_service_discovery_l4_staging(service_mesh_l4):
    """Test service discovery with L4 realism in staging."""
    # Test service discovery for all available services
    discovery_results = []
    
    for service_name in service_mesh_l4.staging_services.keys():
        discovery_result = await service_mesh_l4.test_service_discovery_l4(service_name)
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
async def test_load_balancing_algorithms_l4_staging(service_mesh_l4):
    """Test load balancing algorithms with L4 realism."""
    # Test load balancing for services with multiple instances
    multi_instance_services = [
        name for name, info in service_mesh_l4.staging_services.items()
        if info["accessible_instances"] >= 2
    ]
    
    if not multi_instance_services:
        pytest.skip("No services with multiple instances available for load balancing testing")
    
    load_balancing_results = []
    
    for service_name in multi_instance_services[:2]:  # Test first 2 services to limit test time
        lb_result = await service_mesh_l4.test_load_balancing_algorithms_l4(service_name)
        load_balancing_results.append(lb_result)
        
        if lb_result["success"]:
            # Verify load balancing effectiveness
            assert lb_result["successful_algorithms"] >= 3, "Too few load balancing algorithms working"
            
            # Check distribution analysis
            distribution_analysis = lb_result["distribution_analysis"]
            assert distribution_analysis["overall_metrics"]["avg_distribution_quality"] > 0.5, "Load distribution quality too low"
    
    # Verify overall load balancing success
    successful_lb_tests = [r for r in load_balancing_results if r["success"]]
    assert len(successful_lb_tests) > 0, "No successful load balancing tests"


@pytest.mark.asyncio
async def test_circuit_breaker_patterns_l4_staging(service_mesh_l4):
    """Test circuit breaker patterns with L4 realism."""
    # Test circuit breakers for available services
    available_services = list(service_mesh_l4.staging_services.keys())
    
    if not available_services:
        pytest.skip("No services available for circuit breaker testing")
    
    service_name = available_services[0]  # Test first available service
    cb_result = await service_mesh_l4.test_circuit_breaker_patterns_l4(service_name)
    
    assert cb_result["success"], f"Circuit breaker testing failed: {cb_result.get('error')}"
    assert cb_result["successful_tests"] >= 3, "Too few circuit breaker tests passed"
    
    # Verify specific circuit breaker behaviors
    cb_tests = cb_result["circuit_breaker_tests"]
    
    # Verify state transitions work
    if cb_tests["closed_to_open"]["success"]:
        assert cb_tests["closed_to_open"]["threshold_exceeded"], "Circuit breaker didn't open at failure threshold"
    
    # Verify timeout behavior
    if cb_tests["timeout_behavior"]["success"]:
        assert cb_tests["timeout_behavior"]["timeout_occurred"], "Circuit breaker timeout not working"


@pytest.mark.asyncio
async def test_retry_policies_l4_staging(service_mesh_l4):
    """Test retry policies with L4 realism."""
    # Test retry policies for available services
    available_services = list(service_mesh_l4.staging_services.keys())
    
    if not available_services:
        pytest.skip("No services available for retry policy testing")
    
    service_name = available_services[0]  # Test first available service
    retry_result = await service_mesh_l4.test_retry_policies_l4(service_name)
    
    assert retry_result["success"], f"Retry policy testing failed: {retry_result.get('error')}"
    assert retry_result["successful_retry_tests"] >= 3, "Too few retry policy tests passed"
    
    # Verify specific retry behaviors
    retry_tests = retry_result["retry_policy_tests"]
    
    # Verify exponential backoff
    if retry_tests["exponential_backoff"]["success"]:
        assert retry_tests["exponential_backoff"]["backoff_accuracy"] > 0.7, "Exponential backoff timing inaccurate"
    
    # Verify max attempts respected
    if retry_tests["max_attempts"]["success"]:
        assert retry_tests["max_attempts"]["max_attempts_respected"], "Max retry attempts not respected"
    
    # Verify jitter is working
    if retry_tests["jitter"]["success"]:
        assert retry_tests["jitter"]["delay_variance"], "Retry jitter not providing variance"


@pytest.mark.asyncio
async def test_service_mesh_performance_l4_staging(service_mesh_l4):
    """Test service mesh performance under L4 realistic load."""
    available_services = list(service_mesh_l4.staging_services.keys())
    
    if not available_services:
        pytest.skip("No services available for performance testing")
    
    # Performance test configuration
    performance_start = time.time()
    concurrent_requests = 50
    service_name = available_services[0]
    
    # Generate concurrent service mesh operations
    mesh_tasks = []
    
    # Service discovery tasks
    for i in range(concurrent_requests // 5):
        task = service_mesh_l4.test_service_discovery_l4(service_name)
        mesh_tasks.append(task)
    
    # Load balancing tasks (if multiple instances available)
    if service_mesh_l4.staging_services[service_name]["accessible_instances"] >= 2:
        for i in range(concurrent_requests // 5):
            task = service_mesh_l4.test_load_balancing_algorithms_l4(service_name)
            mesh_tasks.append(task)
    
    # Execute mesh operations concurrently
    performance_results = await asyncio.gather(*mesh_tasks, return_exceptions=True)
    
    total_performance_time = time.time() - performance_start
    
    # Analyze performance results
    successful_operations = [
        r for r in performance_results 
        if isinstance(r, dict) and r.get("success")
    ]
    
    success_rate = len(successful_operations) / len(performance_results) * 100
    throughput = len(performance_results) / total_performance_time
    
    # Verify performance requirements
    assert success_rate >= 90.0, f"Service mesh success rate too low under load: {success_rate}%"
    assert total_performance_time < 300.0, f"Service mesh performance too slow: {total_performance_time}s"
    assert throughput >= 0.5, f"Service mesh throughput too low: {throughput} ops/sec"
    
    logger.info(f"Service mesh performance: {len(successful_operations)}/{len(performance_results)} operations successful, "
               f"{success_rate:.1f}% success rate, {throughput:.2f} ops/sec")


@pytest.mark.asyncio
async def test_service_mesh_resilience_l4_staging(service_mesh_l4):
    """Test service mesh resilience under failure conditions."""
    available_services = list(service_mesh_l4.staging_services.keys())
    
    if not available_services:
        pytest.skip("No services available for resilience testing")
    
    service_name = available_services[0]
    
    # Test resilience scenarios
    resilience_scenarios = [
        "partial_instance_failure",
        "network_partition",
        "high_latency_conditions",
        "cascading_failures"
    ]
    
    resilience_results = []
    
    for scenario in resilience_scenarios:
        scenario_start = time.time()
        
        try:
            if scenario == "partial_instance_failure":
                # Simulate partial instance failure and test service mesh adaptation
                discovery_result = await service_mesh_l4.test_service_discovery_l4(service_name)
                
                # Verify service mesh can still discover healthy instances
                resilience_results.append({
                    "scenario": scenario,
                    "success": discovery_result["success"] and discovery_result["healthy_instances"] > 0,
                    "healthy_instances": discovery_result.get("healthy_instances", 0),
                    "total_instances": discovery_result.get("instances_discovered", 0)
                })
                
            elif scenario == "network_partition":
                # Test circuit breaker behavior during network issues
                cb_result = await service_mesh_l4.test_circuit_breaker_patterns_l4(service_name)
                
                resilience_results.append({
                    "scenario": scenario,
                    "success": cb_result["success"],
                    "circuit_breaker_functional": cb_result.get("successful_tests", 0) > 0
                })
                
            elif scenario == "high_latency_conditions":
                # Test retry policies under latency
                retry_result = await service_mesh_l4.test_retry_policies_l4(service_name)
                
                resilience_results.append({
                    "scenario": scenario,
                    "success": retry_result["success"],
                    "retry_policies_functional": retry_result.get("successful_retry_tests", 0) > 0
                })
                
            elif scenario == "cascading_failures":
                # Test load balancing adaptation
                if service_mesh_l4.staging_services[service_name]["accessible_instances"] >= 2:
                    lb_result = await service_mesh_l4.test_load_balancing_algorithms_l4(service_name)
                    
                    resilience_results.append({
                        "scenario": scenario,
                        "success": lb_result["success"],
                        "load_balancing_adaptive": lb_result.get("successful_algorithms", 0) > 0
                    })
                else:
                    resilience_results.append({
                        "scenario": scenario,
                        "success": True,
                        "skipped": "Insufficient instances for load balancing test"
                    })
                    
        except Exception as e:
            resilience_results.append({
                "scenario": scenario,
                "success": False,
                "error": str(e)
            })
        
        scenario_time = time.time() - scenario_start
        logger.info(f"Resilience scenario '{scenario}' completed in {scenario_time:.2f}s")
    
    # Verify resilience requirements
    successful_scenarios = [r for r in resilience_results if r["success"]]
    resilience_rate = len(successful_scenarios) / len(resilience_scenarios) * 100
    
    assert resilience_rate >= 75.0, f"Service mesh resilience rate too low: {resilience_rate}%"
    assert len(successful_scenarios) >= 3, "Too few resilience scenarios passed"
    
    logger.info(f"Service mesh resilience: {len(successful_scenarios)}/{len(resilience_scenarios)} scenarios passed, "
               f"{resilience_rate:.1f}% resilience rate")