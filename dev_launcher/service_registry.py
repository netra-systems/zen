"""
Service Registry with Retry Logic and Backoff.

This module provides service discovery with retry mechanisms and exponential
backoff to handle timing issues during service startup, addressing test failures
in test_critical_cold_start_initialization.py test 9.

Business Value: Platform/Internal - Stability - Prevents service discovery timing
issues that cause coordinated startup failures.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Status of a service in the registry."""
    REGISTERING = "registering"
    REGISTERED = "registered"
    STARTING = "starting"
    READY = "ready"
    UNHEALTHY = "unhealthy"
    UNREGISTERED = "unregistered"


@dataclass
class ServiceEndpoint:
    """Information about a service endpoint."""
    name: str
    url: str
    port: int
    health_endpoint: Optional[str] = None
    ready_endpoint: Optional[str] = None
    protocol: str = "http"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "url": self.url, 
            "port": self.port,
            "health_endpoint": self.health_endpoint,
            "ready_endpoint": self.ready_endpoint,
            "protocol": self.protocol
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceEndpoint':
        """Create from dictionary."""
        return cls(
            name=data["name"],
            url=data["url"],
            port=data["port"],
            health_endpoint=data.get("health_endpoint"),
            ready_endpoint=data.get("ready_endpoint"),
            protocol=data.get("protocol", "http")
        )


@dataclass
class ServiceRegistration:
    """Complete service registration information."""
    service_name: str
    status: ServiceStatus
    endpoints: List[ServiceEndpoint]
    registered_at: float
    last_seen: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    dependencies: List[str] = field(default_factory=list)
    health_check_interval: float = 30.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "service_name": self.service_name,
            "status": self.status.value,
            "endpoints": [ep.to_dict() for ep in self.endpoints],
            "registered_at": self.registered_at,
            "last_seen": self.last_seen,
            "metadata": self.metadata,
            "tags": list(self.tags),
            "dependencies": self.dependencies,
            "health_check_interval": self.health_check_interval
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceRegistration':
        """Create from dictionary."""
        return cls(
            service_name=data["service_name"],
            status=ServiceStatus(data["status"]),
            endpoints=[ServiceEndpoint.from_dict(ep) for ep in data["endpoints"]],
            registered_at=data["registered_at"],
            last_seen=data["last_seen"],
            metadata=data.get("metadata", {}),
            tags=set(data.get("tags", [])),
            dependencies=data.get("dependencies", []),
            health_check_interval=data.get("health_check_interval", 30.0)
        )


@dataclass
class DiscoveryQuery:
    """Query parameters for service discovery."""
    service_name: Optional[str] = None
    tags: Set[str] = field(default_factory=set)
    status: Optional[ServiceStatus] = None
    dependencies: List[str] = field(default_factory=list)
    include_endpoints: bool = True
    timeout: float = 10.0
    retry_count: int = 3
    retry_delay: float = 1.0
    exponential_backoff: bool = True


class ServiceRegistry:
    """
    Service registry with retry logic and exponential backoff.
    
    Provides reliable service discovery during startup with proper
    retry mechanisms to handle timing issues.
    """
    
    def __init__(self, 
                 registry_dir: Optional[Path] = None,
                 enable_persistence: bool = True,
                 cleanup_interval: float = 60.0):
        """
        Initialize service registry.
        
        Args:
            registry_dir: Directory for persistent storage
            enable_persistence: Whether to persist registry data
            cleanup_interval: Interval between cleanup runs
        """
        self.registry_dir = registry_dir or Path.cwd() / ".service_registry"
        self.enable_persistence = enable_persistence
        self.cleanup_interval = cleanup_interval
        
        self.services: Dict[str, ServiceRegistration] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        if self.enable_persistence:
            self.registry_dir.mkdir(exist_ok=True)
            self._load_persisted_services()
        
        logger.info(f"ServiceRegistry initialized (persistence: {enable_persistence})")
    
    async def start(self) -> None:
        """Start the service registry background tasks."""
        if self._running:
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("ServiceRegistry started")
    
    async def stop(self) -> None:
        """Stop the service registry background tasks."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self.enable_persistence:
            await self._persist_all_services()
        
        logger.info("ServiceRegistry stopped")
    
    async def register_service(self, 
                              service_name: str,
                              endpoints: List[ServiceEndpoint],
                              metadata: Dict[str, Any] = None,
                              tags: Set[str] = None,
                              dependencies: List[str] = None) -> bool:
        """
        Register a service in the registry.
        
        Args:
            service_name: Name of the service
            endpoints: List of service endpoints
            metadata: Additional service metadata
            tags: Service tags
            dependencies: List of service dependencies
            
        Returns:
            True if registration was successful
        """
        metadata = metadata or {}
        tags = tags or set()
        dependencies = dependencies or []
        
        async with self._lock:
            current_time = time.time()
            
            registration = ServiceRegistration(
                service_name=service_name,
                status=ServiceStatus.REGISTERING,
                endpoints=endpoints,
                registered_at=current_time,
                last_seen=current_time,
                metadata=metadata,
                tags=tags,
                dependencies=dependencies
            )
            
            self.services[service_name] = registration
            
            if self.enable_persistence:
                await self._persist_service(service_name)
            
            logger.info(f"Registered service {service_name} with {len(endpoints)} endpoints")
            for endpoint in endpoints:
                logger.debug(f"   ->  {endpoint.name}: {endpoint.url}")
            
            return True
    
    async def update_service_status(self, service_name: str, status: ServiceStatus) -> bool:
        """
        Update the status of a registered service.
        
        Args:
            service_name: Name of the service
            status: New status
            
        Returns:
            True if update was successful
        """
        async with self._lock:
            if service_name not in self.services:
                logger.warning(f"Cannot update status: service {service_name} not registered")
                return False
            
            registration = self.services[service_name]
            old_status = registration.status
            registration.status = status
            registration.last_seen = time.time()
            
            if self.enable_persistence:
                await self._persist_service(service_name)
            
            logger.info(f"Updated service {service_name} status: {old_status.value}  ->  {status.value}")
            return True
    
    async def unregister_service(self, service_name: str) -> bool:
        """
        Unregister a service from the registry.
        
        Args:
            service_name: Name of the service to unregister
            
        Returns:
            True if unregistration was successful
        """
        async with self._lock:
            if service_name not in self.services:
                logger.warning(f"Cannot unregister: service {service_name} not found")
                return False
            
            del self.services[service_name]
            
            if self.enable_persistence:
                service_file = self.registry_dir / f"{service_name}.json"
                if service_file.exists():
                    service_file.unlink()
            
            logger.info(f"Unregistered service {service_name}")
            return True
    
    async def discover_service(self, query: DiscoveryQuery) -> Optional[ServiceRegistration]:
        """
        Discover a single service with retry logic.
        
        Args:
            query: Discovery query parameters
            
        Returns:
            ServiceRegistration if found, None otherwise
        """
        for attempt in range(query.retry_count + 1):
            try:
                async with self._lock:
                    # Refresh from persistence if enabled
                    if self.enable_persistence and query.service_name:
                        await self._refresh_service(query.service_name)
                    
                    # Search for matching service
                    for service_name, registration in self.services.items():
                        if self._matches_query(registration, query):
                            logger.debug(f"Discovered service {service_name} on attempt {attempt + 1}")
                            return registration
                
                # Service not found, maybe it's not registered yet
                if attempt < query.retry_count:
                    delay = self._calculate_retry_delay(query, attempt)
                    logger.debug(f"Service not found, retrying in {delay:.2f}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                
            except Exception as e:
                logger.warning(f"Discovery attempt {attempt + 1} failed: {e}")
                if attempt < query.retry_count:
                    delay = self._calculate_retry_delay(query, attempt)
                    await asyncio.sleep(delay)
        
        # All attempts failed
        if query.service_name:
            logger.error(f"Failed to discover service {query.service_name} after {query.retry_count + 1} attempts")
        else:
            logger.error(f"Failed to discover services matching query after {query.retry_count + 1} attempts")
        
        return None
    
    async def discover_services(self, query: DiscoveryQuery) -> List[ServiceRegistration]:
        """
        Discover multiple services with retry logic.
        
        Args:
            query: Discovery query parameters
            
        Returns:
            List of matching service registrations
        """
        for attempt in range(query.retry_count + 1):
            try:
                async with self._lock:
                    # Refresh from persistence if enabled
                    if self.enable_persistence:
                        await self._refresh_all_services()
                    
                    # Find all matching services
                    matches = []
                    for service_name, registration in self.services.items():
                        if self._matches_query(registration, query):
                            matches.append(registration)
                    
                    if matches:
                        logger.debug(f"Discovered {len(matches)} services on attempt {attempt + 1}")
                        return matches
                
                # No matches found
                if attempt < query.retry_count:
                    delay = self._calculate_retry_delay(query, attempt)
                    logger.debug(f"No matching services found, retrying in {delay:.2f}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                
            except Exception as e:
                logger.warning(f"Discovery attempt {attempt + 1} failed: {e}")
                if attempt < query.retry_count:
                    delay = self._calculate_retry_delay(query, attempt)
                    await asyncio.sleep(delay)
        
        logger.error(f"Failed to discover services after {query.retry_count + 1} attempts")
        return []
    
    async def wait_for_service(self, 
                              service_name: str, 
                              status: ServiceStatus = ServiceStatus.READY,
                              timeout: float = 60.0,
                              check_interval: float = 1.0) -> Optional[ServiceRegistration]:
        """
        Wait for a service to reach a specific status.
        
        Args:
            service_name: Name of the service to wait for
            status: Status to wait for
            timeout: Maximum time to wait
            check_interval: Time between checks
            
        Returns:
            ServiceRegistration if service reaches status, None if timeout
        """
        start_time = time.time()
        
        logger.info(f"Waiting for service {service_name} to reach status {status.value} (timeout: {timeout}s)")
        
        while (time.time() - start_time) < timeout:
            query = DiscoveryQuery(
                service_name=service_name,
                status=status,
                retry_count=1,
                retry_delay=0.1
            )
            
            registration = await self.discover_service(query)
            if registration:
                elapsed = time.time() - start_time
                logger.info(f"Service {service_name} reached status {status.value} after {elapsed:.2f}s")
                return registration
            
            await asyncio.sleep(check_interval)
        
        elapsed = time.time() - start_time
        logger.error(f"Timeout waiting for service {service_name} to reach status {status.value} after {elapsed:.2f}s")
        return None
    
    async def wait_for_dependencies(self, 
                                  service_name: str,
                                  timeout: float = 120.0) -> Tuple[bool, List[str]]:
        """
        Wait for all dependencies of a service to be ready.
        
        Args:
            service_name: Name of the service
            timeout: Maximum time to wait
            
        Returns:
            Tuple of (all_ready, failed_dependencies)
        """
        # Get service registration
        async with self._lock:
            if service_name not in self.services:
                logger.error(f"Service {service_name} not registered")
                return False, [service_name]
        
        registration = self.services[service_name]
        dependencies = registration.dependencies
        
        if not dependencies:
            logger.debug(f"Service {service_name} has no dependencies")
            return True, []
        
        logger.info(f"Waiting for dependencies of {service_name}: {dependencies}")
        
        start_time = time.time()
        failed_dependencies = []
        
        # Wait for each dependency
        for dep_name in dependencies:
            remaining_time = timeout - (time.time() - start_time)
            if remaining_time <= 0:
                failed_dependencies.append(dep_name)
                continue
            
            dep_registration = await self.wait_for_service(
                service_name=dep_name,
                status=ServiceStatus.READY,
                timeout=remaining_time
            )
            
            if not dep_registration:
                failed_dependencies.append(dep_name)
        
        success = len(failed_dependencies) == 0
        elapsed = time.time() - start_time
        
        if success:
            logger.info(f"All dependencies ready for {service_name} after {elapsed:.2f}s")
        else:
            logger.error(f"Failed dependencies for {service_name} after {elapsed:.2f}s: {failed_dependencies}")
        
        return success, failed_dependencies
    
    def _matches_query(self, registration: ServiceRegistration, query: DiscoveryQuery) -> bool:
        """Check if a service registration matches a query."""
        # Check service name
        if query.service_name and registration.service_name != query.service_name:
            return False
        
        # Check status
        if query.status and registration.status != query.status:
            return False
        
        # Check tags
        if query.tags and not query.tags.issubset(registration.tags):
            return False
        
        # Check dependencies
        if query.dependencies:
            for dep in query.dependencies:
                if dep not in registration.dependencies:
                    return False
        
        return True
    
    def _calculate_retry_delay(self, query: DiscoveryQuery, attempt: int) -> float:
        """Calculate retry delay with optional exponential backoff."""
        base_delay = query.retry_delay
        
        if query.exponential_backoff:
            return base_delay * (2 ** attempt)
        else:
            return base_delay
    
    async def _refresh_service(self, service_name: str) -> None:
        """Refresh a service from persistent storage."""
        if not self.enable_persistence:
            return
        
        service_file = self.registry_dir / f"{service_name}.json"
        if service_file.exists():
            try:
                with open(service_file, 'r') as f:
                    data = json.load(f)
                    registration = ServiceRegistration.from_dict(data)
                    self.services[service_name] = registration
            except Exception as e:
                logger.warning(f"Failed to refresh service {service_name}: {e}")
    
    async def _refresh_all_services(self) -> None:
        """Refresh all services from persistent storage."""
        if not self.enable_persistence:
            return
        
        try:
            for service_file in self.registry_dir.glob("*.json"):
                service_name = service_file.stem
                if service_name not in self.services:
                    await self._refresh_service(service_name)
        except Exception as e:
            logger.warning(f"Failed to refresh services: {e}")
    
    async def _persist_service(self, service_name: str) -> None:
        """Persist a service registration to storage."""
        if not self.enable_persistence:
            return
        
        if service_name not in self.services:
            return
        
        try:
            service_file = self.registry_dir / f"{service_name}.json"
            registration = self.services[service_name]
            
            with open(service_file, 'w') as f:
                json.dump(registration.to_dict(), f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to persist service {service_name}: {e}")
    
    async def _persist_all_services(self) -> None:
        """Persist all service registrations."""
        for service_name in self.services.keys():
            await self._persist_service(service_name)
    
    def _load_persisted_services(self) -> None:
        """Load persisted services on startup."""
        if not self.enable_persistence or not self.registry_dir.exists():
            return
        
        try:
            for service_file in self.registry_dir.glob("*.json"):
                try:
                    with open(service_file, 'r') as f:
                        data = json.load(f)
                        registration = ServiceRegistration.from_dict(data)
                        self.services[registration.service_name] = registration
                        logger.debug(f"Loaded persisted service: {registration.service_name}")
                except Exception as e:
                    logger.warning(f"Failed to load persisted service from {service_file}: {e}")
            
            if self.services:
                logger.info(f"Loaded {len(self.services)} persisted services")
        except Exception as e:
            logger.warning(f"Failed to load persisted services: {e}")
    
    async def _cleanup_loop(self) -> None:
        """Background task to clean up stale services."""
        while self._running:
            try:
                await self._cleanup_stale_services()
                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(self.cleanup_interval)
    
    async def _cleanup_stale_services(self) -> None:
        """Clean up stale service registrations."""
        current_time = time.time()
        stale_threshold = 300.0  # 5 minutes
        stale_services = []
        
        async with self._lock:
            for service_name, registration in self.services.items():
                if (current_time - registration.last_seen) > stale_threshold:
                    if registration.status not in [ServiceStatus.READY, ServiceStatus.STARTING]:
                        stale_services.append(service_name)
            
            for service_name in stale_services:
                logger.info(f"Cleaning up stale service: {service_name}")
                del self.services[service_name]
                
                if self.enable_persistence:
                    service_file = self.registry_dir / f"{service_name}.json"
                    if service_file.exists():
                        service_file.unlink()
    
    def get_registry_status(self) -> Dict[str, Any]:
        """Get comprehensive registry status."""
        current_time = time.time()
        
        status = {
            "total_services": len(self.services),
            "services_by_status": {},
            "services": {},
            "persistence_enabled": self.enable_persistence,
            "registry_dir": str(self.registry_dir) if self.enable_persistence else None
        }
        
        # Count services by status
        for registration in self.services.values():
            status_name = registration.status.value
            if status_name not in status["services_by_status"]:
                status["services_by_status"][status_name] = 0
            status["services_by_status"][status_name] += 1
        
        # Individual service details
        for service_name, registration in self.services.items():
            service_info = {
                "status": registration.status.value,
                "endpoints": len(registration.endpoints),
                "dependencies": registration.dependencies,
                "tags": list(registration.tags),
                "registered_at": registration.registered_at,
                "last_seen": registration.last_seen,
                "age": current_time - registration.registered_at
            }
            
            status["services"][service_name] = service_info
        
        return status


# Global service registry instance
_global_registry: Optional[ServiceRegistry] = None


async def get_global_service_registry() -> ServiceRegistry:
    """Get or create the global service registry instance."""
    global _global_registry
    
    if _global_registry is None:
        _global_registry = ServiceRegistry()
        await _global_registry.start()
    
    return _global_registry


async def cleanup_global_service_registry() -> None:
    """Clean up the global service registry instance."""
    global _global_registry
    
    if _global_registry:
        await _global_registry.stop()
        _global_registry = None