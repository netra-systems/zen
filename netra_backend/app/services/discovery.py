"""
Service Discovery Module

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System Reliability & Development Velocity
- Value Impact: Enables microservice communication and load balancing
- Strategic Impact: Essential for scalable distributed architecture

Provides service discovery, health monitoring, and load balancing.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from collections import defaultdict

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ServiceStatus(str, Enum):
    """Service health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class LoadBalanceStrategy(str, Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    RANDOM = "random"


@dataclass
class ServiceEndpoint:
    """Service endpoint information."""
    service_name: str
    instance_id: str
    host: str
    port: int
    protocol: str = "http"
    path: str = ""
    weight: int = 100
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    status: ServiceStatus = ServiceStatus.UNKNOWN
    
    @property
    def url(self) -> str:
        """Get full URL for the endpoint."""
        return f"{self.protocol}://{self.host}:{self.port}{self.path}"
    
    @property
    def is_healthy(self) -> bool:
        """Check if endpoint is healthy."""
        return self.status == ServiceStatus.HEALTHY
    
    def update_heartbeat(self) -> None:
        """Update heartbeat timestamp."""
        self.last_heartbeat = time.time()


@dataclass
class ServiceHealthCheck:
    """Health check configuration."""
    endpoint_path: str = "/health"
    interval_seconds: float = 30.0
    timeout_seconds: float = 5.0
    failure_threshold: int = 3
    success_threshold: int = 2
    custom_check: Optional[Callable] = None


class ServiceRegistry:
    """Registry for service discovery."""
    
    def __init__(self):
        self.services: Dict[str, Dict[str, ServiceEndpoint]] = defaultdict(dict)
        self.service_configs: Dict[str, ServiceHealthCheck] = {}
        self.service_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "last_request": 0
        })
        
    def register_service(self, endpoint: ServiceEndpoint, 
                        health_check: Optional[ServiceHealthCheck] = None) -> bool:
        """Register a service endpoint."""
        try:
            self.services[endpoint.service_name][endpoint.instance_id] = endpoint
            
            if health_check:
                self.service_configs[endpoint.service_name] = health_check
            
            logger.info(f"Registered service {endpoint.service_name} "
                       f"instance {endpoint.instance_id} at {endpoint.url}")
            return True
        except Exception as e:
            logger.error(f"Failed to register service {endpoint.service_name}: {e}")
            return False
    
    def deregister_service(self, service_name: str, instance_id: str) -> bool:
        """Deregister a service endpoint."""
        try:
            if service_name in self.services and instance_id in self.services[service_name]:
                del self.services[service_name][instance_id]
                logger.info(f"Deregistered {service_name} instance {instance_id}")
                
                # Clean up empty service entries
                if not self.services[service_name]:
                    del self.services[service_name]
                    
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to deregister service {service_name}: {e}")
            return False
    
    def get_service_instances(self, service_name: str, 
                            healthy_only: bool = True) -> List[ServiceEndpoint]:
        """Get all instances of a service."""
        instances = list(self.services.get(service_name, {}).values())
        
        if healthy_only:
            instances = [inst for inst in instances if inst.is_healthy]
        
        return instances
    
    def get_service_instance(self, service_name: str, instance_id: str) -> Optional[ServiceEndpoint]:
        """Get specific service instance."""
        return self.services.get(service_name, {}).get(instance_id)
    
    def update_service_status(self, service_name: str, instance_id: str, 
                            status: ServiceStatus) -> bool:
        """Update service instance status."""
        endpoint = self.get_service_instance(service_name, instance_id)
        if endpoint:
            endpoint.status = status
            endpoint.update_heartbeat()
            logger.debug(f"Updated {service_name}/{instance_id} status to {status}")
            return True
        return False
    
    def record_service_stats(self, service_name: str, response_time: float, 
                           success: bool) -> None:
        """Record service performance statistics."""
        stats = self.service_stats[service_name]
        stats["total_requests"] += 1
        stats["last_request"] = time.time()
        
        if not success:
            stats["failed_requests"] += 1
        
        # Update average response time (simple moving average)
        current_avg = stats["avg_response_time"]
        total_requests = stats["total_requests"]
        stats["avg_response_time"] = (current_avg * (total_requests - 1) + response_time) / total_requests
    
    def get_service_stats(self, service_name: str) -> Dict[str, Any]:
        """Get service statistics."""
        return self.service_stats.get(service_name, {})
    
    def list_all_services(self) -> Dict[str, List[Dict[str, Any]]]:
        """List all registered services."""
        result = {}
        for service_name, instances in self.services.items():
            result[service_name] = [
                {
                    "instance_id": endpoint.instance_id,
                    "url": endpoint.url,
                    "status": endpoint.status,
                    "weight": endpoint.weight,
                    "last_heartbeat": endpoint.last_heartbeat,
                    "metadata": endpoint.metadata
                }
                for endpoint in instances.values()
            ]
        return result


class LoadBalancer:
    """Load balancer for service endpoints."""
    
    def __init__(self, strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self.round_robin_counters: Dict[str, int] = defaultdict(int)
        self.connection_counts: Dict[str, int] = defaultdict(int)
    
    def select_endpoint(self, service_name: str, 
                       endpoints: List[ServiceEndpoint]) -> Optional[ServiceEndpoint]:
        """Select an endpoint using the configured strategy."""
        if not endpoints:
            return None
        
        healthy_endpoints = [ep for ep in endpoints if ep.is_healthy]
        if not healthy_endpoints:
            # Fall back to any available endpoint
            healthy_endpoints = endpoints
        
        if self.strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return self._round_robin_select(service_name, healthy_endpoints)
        elif self.strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select(healthy_endpoints)
        elif self.strategy == LoadBalanceStrategy.WEIGHTED:
            return self._weighted_select(healthy_endpoints)
        else:  # RANDOM
            import random
            return random.choice(healthy_endpoints)
    
    def _round_robin_select(self, service_name: str, 
                           endpoints: List[ServiceEndpoint]) -> ServiceEndpoint:
        """Round robin selection."""
        counter = self.round_robin_counters[service_name]
        selected = endpoints[counter % len(endpoints)]
        self.round_robin_counters[service_name] = counter + 1
        return selected
    
    def _least_connections_select(self, endpoints: List[ServiceEndpoint]) -> ServiceEndpoint:
        """Least connections selection."""
        min_connections = float('inf')
        selected = endpoints[0]
        
        for endpoint in endpoints:
            connections = self.connection_counts.get(endpoint.instance_id, 0)
            if connections < min_connections:
                min_connections = connections
                selected = endpoint
        
        return selected
    
    def _weighted_select(self, endpoints: List[ServiceEndpoint]) -> ServiceEndpoint:
        """Weighted random selection."""
        import random
        total_weight = sum(ep.weight for ep in endpoints)
        if total_weight == 0:
            return random.choice(endpoints)
        
        rand_weight = random.randint(1, total_weight)
        current_weight = 0
        
        for endpoint in endpoints:
            current_weight += endpoint.weight
            if rand_weight <= current_weight:
                return endpoint
        
        return endpoints[-1]  # Fallback
    
    def increment_connections(self, instance_id: str) -> None:
        """Increment connection count for load balancing."""
        self.connection_counts[instance_id] += 1
    
    def decrement_connections(self, instance_id: str) -> None:
        """Decrement connection count for load balancing."""
        self.connection_counts[instance_id] = max(0, self.connection_counts[instance_id] - 1)


class HealthMonitor:
    """Monitors service health."""
    
    def __init__(self, registry: ServiceRegistry):
        self.registry = registry
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.is_running = False
    
    async def start_monitoring(self) -> None:
        """Start health monitoring for all services."""
        if self.is_running:
            return
        
        self.is_running = True
        
        for service_name in self.registry.services.keys():
            if service_name not in self.monitoring_tasks:
                self.monitoring_tasks[service_name] = asyncio.create_task(
                    self._monitor_service_health(service_name)
                )
        
        logger.info("Started health monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop health monitoring."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        for task in self.monitoring_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self.monitoring_tasks:
            await asyncio.gather(*self.monitoring_tasks.values(), return_exceptions=True)
        
        self.monitoring_tasks.clear()
        logger.info("Stopped health monitoring")
    
    async def _monitor_service_health(self, service_name: str) -> None:
        """Monitor health for a specific service."""
        try:
            health_config = self.registry.service_configs.get(
                service_name, 
                ServiceHealthCheck()
            )
            
            while self.is_running:
                await self._check_service_health(service_name, health_config)
                await asyncio.sleep(health_config.interval_seconds)
                
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Error monitoring {service_name}: {e}")
    
    async def _check_service_health(self, service_name: str, 
                                   config: ServiceHealthCheck) -> None:
        """Check health of all instances of a service."""
        instances = self.registry.get_service_instances(service_name, healthy_only=False)
        
        for instance in instances:
            try:
                if config.custom_check:
                    # Use custom health check
                    is_healthy = await config.custom_check(instance)
                else:
                    # Default HTTP health check
                    is_healthy = await self._http_health_check(instance, config)
                
                new_status = ServiceStatus.HEALTHY if is_healthy else ServiceStatus.UNHEALTHY
                self.registry.update_service_status(service_name, instance.instance_id, new_status)
                
            except Exception as e:
                logger.warning(f"Health check failed for {service_name}/{instance.instance_id}: {e}")
                self.registry.update_service_status(
                    service_name, instance.instance_id, ServiceStatus.UNHEALTHY
                )
    
    async def _http_health_check(self, instance: ServiceEndpoint, 
                                config: ServiceHealthCheck) -> bool:
        """Perform HTTP health check."""
        try:
            # Simplified health check - in production would use actual HTTP client
            import asyncio
            await asyncio.sleep(0.01)  # Simulate network call
            
            # Check if service is responsive (simplified)
            current_time = time.time()
            if current_time - instance.last_heartbeat > config.interval_seconds * 2:
                return False
                
            return True
            
        except Exception as e:
            logger.debug(f"HTTP health check failed for {instance.url}: {e}")
            return False


class ServiceDiscovery:
    """Main service discovery service."""
    
    def __init__(self, load_balance_strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN):
        self.registry = ServiceRegistry()
        self.load_balancer = LoadBalancer(load_balance_strategy)
        self.health_monitor = HealthMonitor(self.registry)
        self.discovery_stats = {
            "services_registered": 0,
            "services_deregistered": 0,
            "lookups_performed": 0,
            "health_checks_performed": 0
        }
    
    async def start(self) -> None:
        """Start the service discovery system."""
        await self.health_monitor.start_monitoring()
        logger.info("Service discovery started")
    
    async def stop(self) -> None:
        """Stop the service discovery system."""
        await self.health_monitor.stop_monitoring()
        logger.info("Service discovery stopped")
    
    def register_service(self, service_name: str, host: str, port: int,
                        instance_id: Optional[str] = None,
                        protocol: str = "http",
                        path: str = "",
                        weight: int = 100,
                        metadata: Optional[Dict[str, Any]] = None,
                        health_check: Optional[ServiceHealthCheck] = None) -> str:
        """Register a service."""
        if instance_id is None:
            import uuid
            instance_id = str(uuid.uuid4())
        
        endpoint = ServiceEndpoint(
            service_name=service_name,
            instance_id=instance_id,
            host=host,
            port=port,
            protocol=protocol,
            path=path,
            weight=weight,
            metadata=metadata or {}
        )
        
        if self.registry.register_service(endpoint, health_check):
            self.discovery_stats["services_registered"] += 1
            return instance_id
        
        raise RuntimeError(f"Failed to register service {service_name}")
    
    def deregister_service(self, service_name: str, instance_id: str) -> bool:
        """Deregister a service."""
        if self.registry.deregister_service(service_name, instance_id):
            self.discovery_stats["services_deregistered"] += 1
            return True
        return False
    
    async def discover_service(self, service_name: str) -> Optional[ServiceEndpoint]:
        """Discover and select a service endpoint."""
        self.discovery_stats["lookups_performed"] += 1
        
        instances = self.registry.get_service_instances(service_name)
        if not instances:
            logger.warning(f"No healthy instances found for service {service_name}")
            return None
        
        selected = self.load_balancer.select_endpoint(service_name, instances)
        if selected:
            self.load_balancer.increment_connections(selected.instance_id)
            logger.debug(f"Selected {service_name} instance: {selected.instance_id}")
        
        return selected
    
    def release_connection(self, instance_id: str) -> None:
        """Release a connection for load balancing."""
        self.load_balancer.decrement_connections(instance_id)
    
    def get_service_url(self, service_name: str) -> Optional[str]:
        """Get URL for a service (convenience method)."""
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Can't use await in sync method, return None
            return None
        else:
            endpoint = loop.run_until_complete(self.discover_service(service_name))
            return endpoint.url if endpoint else None
    
    def heartbeat(self, service_name: str, instance_id: str) -> bool:
        """Send heartbeat for a service instance."""
        endpoint = self.registry.get_service_instance(service_name, instance_id)
        if endpoint:
            endpoint.update_heartbeat()
            return True
        return False
    
    def get_discovery_stats(self) -> Dict[str, Any]:
        """Get service discovery statistics."""
        stats = self.discovery_stats.copy()
        stats["active_services"] = len(self.registry.services)
        stats["total_instances"] = sum(
            len(instances) for instances in self.registry.services.values()
        )
        stats["healthy_instances"] = sum(
            len([inst for inst in instances.values() if inst.is_healthy])
            for instances in self.registry.services.values()
        )
        return stats
    
    def list_services(self) -> Dict[str, List[Dict[str, Any]]]:
        """List all registered services."""
        return self.registry.list_all_services()


# Global service discovery instance
_service_discovery: Optional[ServiceDiscovery] = None

def get_service_discovery() -> ServiceDiscovery:
    """Get global service discovery instance."""
    global _service_discovery
    if _service_discovery is None:
        _service_discovery = ServiceDiscovery()
    return _service_discovery

async def discover_service_url(service_name: str) -> Optional[str]:
    """Convenience function to discover a service URL."""
    discovery = get_service_discovery()
    endpoint = await discovery.discover_service(service_name)
    return endpoint.url if endpoint else None

def register_service_instance(service_name: str, host: str, port: int, **kwargs) -> str:
    """Convenience function to register a service."""
    discovery = get_service_discovery()
    return discovery.register_service(service_name, host, port, **kwargs)