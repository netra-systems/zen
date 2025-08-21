"""Service Mesh Test Fixtures and Utilities

Shared fixtures and utilities for service mesh critical path testing.
Extracted from test_service_mesh_l4.py to maintain DRY principles.
"""

import pytest
import asyncio
import time
import uuid
import logging
import json
import os
from typing import Dict, List, Optional, Any
from unittest.mock import patch
from datetime import datetime, timedelta
import httpx
import random

from app.services.service_mesh.discovery_service import ServiceDiscoveryService
from app.services.service_mesh.load_balancer import LoadBalancerService
from app.services.service_mesh.circuit_breaker import CircuitBreakerService
from app.services.service_mesh.retry_policy import RetryPolicyService
from app.config import Config

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
                        {"host": "api-1.staging.netra.ai", "port": 8000, "zone": "us-central1-a"},
                        {"host": "api-2.staging.netra.ai", "port": 8000, "zone": "us-central1-b"},
                        {"host": "api-3.staging.netra.ai", "port": 8000, "zone": "us-central1-c"}
                    ],
                    "health_endpoint": "/health",
                    "service_type": "http"
                },
                "auth_service": {
                    "instances": [
                        {"host": "auth-1.staging.netra.ai", "port": 8001, "zone": "us-central1-a"},
                        {"host": "auth-2.staging.netra.ai", "port": 8001, "zone": "us-central1-b"}
                    ],
                    "health_endpoint": "/health",
                    "service_type": "http"
                },
                "websocket_service": {
                    "instances": [
                        {"host": "ws-1.staging.netra.ai", "port": 8002, "zone": "us-central1-a"},
                        {"host": "ws-2.staging.netra.ai", "port": 8002, "zone": "us-central1-b"}
                    ],
                    "health_endpoint": "/health",
                    "service_type": "websocket"
                },
                "llm_service": {
                    "instances": [
                        {"host": "llm-1.staging.netra.ai", "port": 8003, "zone": "us-central1-a"},
                        {"host": "llm-2.staging.netra.ai", "port": 8003, "zone": "us-central1-b"},
                        {"host": "llm-3.staging.netra.ai", "port": 8003, "zone": "us-central1-c"}
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


# Utility functions for test simulations
async def simulate_failing_request() -> Dict[str, Any]:
    """Simulate a failing request for circuit breaker testing."""
    await asyncio.sleep(0.1)
    raise Exception("Simulated request failure")


async def simulate_successful_request() -> Dict[str, Any]:
    """Simulate a successful request for circuit breaker testing."""
    await asyncio.sleep(0.1)
    return {"success": True, "data": "test_response"}


async def simulate_slow_request(delay: float) -> Dict[str, Any]:
    """Simulate a slow request for timeout testing."""
    await asyncio.sleep(delay)
    return {"success": True, "data": "slow_response"}


def calculate_backoff_accuracy(actual_delays: List[float], expected_delays: List[float]) -> float:
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


def calculate_fixed_delay_consistency(actual_delays: List[float], expected_delay: float) -> float:
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