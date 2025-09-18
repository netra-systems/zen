"""
API Gateway Load Balancer

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide load balancing functionality for tests
- Value Impact: Enables load balancing tests to execute without import errors
- Strategic Impact: Enables load balancing functionality validation
"""

import asyncio
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class LoadBalancingStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    LEAST_CONNECTIONS = "least_connections"
    RANDOM = "random"


@dataclass
class ServiceEndpoint:
    """Service endpoint configuration."""
    host: str
    port: int
    weight: int = 1
    health_status: str = "healthy"  # healthy, unhealthy, unknown
    connections: int = 0  # Active connections (for least_connections)
    last_health_check: Optional[float] = None


class LoadBalancer:
    """Advanced load balancer for distributing requests across service endpoints."""
    
    def __init__(self):
        self.services: Dict[str, List[ServiceEndpoint]] = {}
        self.round_robin_indices: Dict[str, int] = {}
        self.health_check_interval = 30  # seconds
        self.last_health_checks: Dict[str, float] = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize the load balancer."""
        self._initialized = True
        logger.info("Load balancer initialized")
    
    async def shutdown(self):
        """Shutdown the load balancer."""
        self._initialized = False
        logger.info("Load balancer shutdown")
    
    def register_service(self, service_name: str, endpoints: List[ServiceEndpoint]):
        """Register service endpoints."""
        self.services[service_name] = endpoints
        self.round_robin_indices[service_name] = 0
        self.last_health_checks[service_name] = time.time()
        logger.info(f"Registered service {service_name} with {len(endpoints)} endpoints")
    
    def add_endpoint(self, service_name: str, endpoint: ServiceEndpoint):
        """Add an endpoint to a service."""
        if service_name not in self.services:
            self.services[service_name] = []
        
        self.services[service_name].append(endpoint)
        logger.info(f"Added endpoint {endpoint.host}:{endpoint.port} to service {service_name}")
    
    def remove_endpoint(self, service_name: str, host: str, port: int):
        """Remove an endpoint from a service."""
        if service_name in self.services:
            self.services[service_name] = [
                ep for ep in self.services[service_name] 
                if not (ep.host == host and ep.port == port)
            ]
            logger.info(f"Removed endpoint {host}:{port} from service {service_name}")
    
    async def get_endpoint(self, service_name: str, strategy: str = "round_robin") -> Optional[ServiceEndpoint]:
        """Get next endpoint based on load balancing strategy."""
        if service_name not in self.services:
            logger.warning(f"Service {service_name} not found")
            return None
        
        endpoints = self.services[service_name]
        healthy_endpoints = [ep for ep in endpoints if ep.health_status == "healthy"]
        
        if not healthy_endpoints:
            logger.warning(f"No healthy endpoints for service {service_name}")
            return None
        
        # Select endpoint based on strategy
        if strategy == LoadBalancingStrategy.ROUND_ROBIN.value:
            return self._get_round_robin_endpoint(service_name, healthy_endpoints)
        elif strategy == LoadBalancingStrategy.WEIGHTED.value:
            return self._get_weighted_endpoint(healthy_endpoints)
        elif strategy == LoadBalancingStrategy.LEAST_CONNECTIONS.value:
            return self._get_least_connections_endpoint(healthy_endpoints)
        elif strategy == LoadBalancingStrategy.RANDOM.value:
            return random.choice(healthy_endpoints)
        else:
            # Default to round robin
            return self._get_round_robin_endpoint(service_name, healthy_endpoints)
    
    def _get_round_robin_endpoint(self, service_name: str, endpoints: List[ServiceEndpoint]) -> ServiceEndpoint:
        """Get endpoint using round-robin strategy."""
        current_index = self.round_robin_indices.get(service_name, 0)
        endpoint = endpoints[current_index % len(endpoints)]
        
        # Update index for next request
        self.round_robin_indices[service_name] = (current_index + 1) % len(endpoints)
        
        return endpoint
    
    def _get_weighted_endpoint(self, endpoints: List[ServiceEndpoint]) -> ServiceEndpoint:
        """Get endpoint using weighted random strategy."""
        total_weight = sum(ep.weight for ep in endpoints)
        
        if total_weight == 0:
            return random.choice(endpoints)
        
        # Generate random number between 0 and total_weight
        rand_weight = random.uniform(0, total_weight)
        current_weight = 0
        
        for endpoint in endpoints:
            current_weight += endpoint.weight
            if rand_weight <= current_weight:
                return endpoint
        
        # Fallback to last endpoint
        return endpoints[-1]
    
    def _get_least_connections_endpoint(self, endpoints: List[ServiceEndpoint]) -> ServiceEndpoint:
        """Get endpoint with least active connections."""
        return min(endpoints, key=lambda ep: ep.connections)
    
    def increment_connections(self, endpoint: ServiceEndpoint):
        """Increment active connections for an endpoint."""
        endpoint.connections += 1
    
    def decrement_connections(self, endpoint: ServiceEndpoint):
        """Decrement active connections for an endpoint."""
        endpoint.connections = max(0, endpoint.connections - 1)
    
    def update_endpoint_health(self, service_name: str, host: str, port: int, 
                             health_status: str):
        """Update health status of a specific endpoint."""
        if service_name in self.services:
            for endpoint in self.services[service_name]:
                if endpoint.host == host and endpoint.port == port:
                    endpoint.health_status = health_status
                    endpoint.last_health_check = time.time()
                    logger.info(f"Updated health status for {host}:{port} to {health_status}")
                    break
    
    def get_service_health(self, service_name: str) -> Dict[str, Any]:
        """Get health status of all endpoints for a service."""
        if service_name not in self.services:
            return {"error": "Service not found"}
        
        endpoints = self.services[service_name]
        healthy_count = sum(1 for ep in endpoints if ep.health_status == "healthy")
        
        return {
            "service_name": service_name,
            "total_endpoints": len(endpoints),
            "healthy_endpoints": healthy_count,
            "unhealthy_endpoints": len(endpoints) - healthy_count,
            "endpoints": [
                {
                    "host": ep.host,
                    "port": ep.port,
                    "weight": ep.weight,
                    "health_status": ep.health_status,
                    "connections": ep.connections,
                    "last_health_check": ep.last_health_check
                }
                for ep in endpoints
            ]
        }
    
    def get_all_services_health(self) -> Dict[str, Any]:
        """Get health status of all services."""
        return {
            service_name: self.get_service_health(service_name)
            for service_name in self.services.keys()
        }