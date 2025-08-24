"""
Service Dependency Management System.

This module provides dependency resolution and ordering for service startup.
Uses topological sorting to ensure services start in the correct order.

Business Value: Platform/Internal - Stability - Prevents service startup failures
by ensuring dependencies are ready before dependent services start.
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class DependencyType(Enum):
    """Types of dependencies between services."""
    REQUIRED = "required"  # Service cannot start without this dependency
    OPTIONAL = "optional"  # Service can start without this dependency
    SOFT = "soft"  # Preferred to have but not blocking


@dataclass
class ServiceDependency:
    """Represents a dependency between services."""
    service: str
    depends_on: str
    dependency_type: DependencyType
    timeout: int = 30  # Max time to wait for dependency
    retry_interval: float = 1.0  # Time between checks
    description: Optional[str] = None


@dataclass
class ServiceInfo:
    """Information about a service including its state and dependencies."""
    name: str
    state: str = "pending"  # pending, starting, ready, failed
    dependencies: List[ServiceDependency] = None
    startup_time: Optional[float] = None
    ready_time: Optional[float] = None
    failure_reason: Optional[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class DependencyManager:
    """
    Manages service dependencies and startup ordering.
    
    Provides topological sorting for dependency resolution and tracks
    service states to ensure proper startup order.
    """
    
    def __init__(self):
        """Initialize dependency manager."""
        self.services: Dict[str, ServiceInfo] = {}
        self.dependency_graph: Dict[str, List[str]] = defaultdict(list)
        self.reverse_graph: Dict[str, List[str]] = defaultdict(list)
        self.startup_order: List[str] = []
        self._lock = asyncio.Lock()
        
        logger.info("DependencyManager initialized")
    
    def add_service(self, service_name: str, dependencies: List[ServiceDependency] = None) -> None:
        """
        Add a service with its dependencies.
        
        Args:
            service_name: Name of the service
            dependencies: List of dependencies for this service
        """
        if dependencies is None:
            dependencies = []
            
        self.services[service_name] = ServiceInfo(
            name=service_name,
            dependencies=dependencies
        )
        
        # Update dependency graph
        for dep in dependencies:
            self.dependency_graph[service_name].append(dep.depends_on)
            self.reverse_graph[dep.depends_on].append(service_name)
        
        logger.info(f"Added service {service_name} with {len(dependencies)} dependencies")
        for dep in dependencies:
            logger.debug(f"  → {service_name} depends on {dep.depends_on} ({dep.dependency_type.value})")
    
    def get_startup_order(self) -> List[str]:
        """
        Get the order in which services should be started using topological sorting.
        
        Returns:
            List of service names in startup order
            
        Raises:
            ValueError: If circular dependencies are detected
        """
        if not self.services:
            return []
        
        # Use Kahn's algorithm for topological sorting
        in_degree = defaultdict(int)
        graph = defaultdict(list)
        
        # Build graph considering only REQUIRED dependencies
        for service_name, service_info in self.services.items():
            for dep in service_info.dependencies:
                if dep.dependency_type == DependencyType.REQUIRED:
                    graph[dep.depends_on].append(service_name)
                    in_degree[service_name] += 1
            
            # Ensure all services are in in_degree map
            if service_name not in in_degree:
                in_degree[service_name] = 0
        
        # Initialize queue with services having no dependencies
        queue = deque([service for service, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            # Remove edges from current service
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Check for circular dependencies
        if len(result) != len(self.services):
            remaining_services = set(self.services.keys()) - set(result)
            raise ValueError(f"Circular dependency detected involving services: {remaining_services}")
        
        self.startup_order = result
        logger.info(f"Computed startup order: {' → '.join(result)}")
        return result
    
    async def wait_for_dependencies(self, service_name: str) -> bool:
        """
        Wait for all dependencies of a service to be ready.
        
        Args:
            service_name: Name of the service to wait for dependencies
            
        Returns:
            True if all required dependencies are ready, False otherwise
        """
        if service_name not in self.services:
            logger.error(f"Service {service_name} not found in dependency manager")
            return False
        
        service_info = self.services[service_name]
        logger.info(f"Waiting for dependencies of {service_name}")
        
        dependency_results = []
        
        # Check each dependency
        for dep in service_info.dependencies:
            result = await self._wait_for_single_dependency(service_name, dep)
            dependency_results.append(result)
            
            if not result and dep.dependency_type == DependencyType.REQUIRED:
                logger.error(f"Required dependency {dep.depends_on} failed for {service_name}")
                return False
            elif not result:
                logger.warning(f"Optional dependency {dep.depends_on} not available for {service_name}")
        
        # All required dependencies are satisfied
        ready_deps = [dep.depends_on for dep, result in zip(service_info.dependencies, dependency_results) if result]
        failed_deps = [dep.depends_on for dep, result in zip(service_info.dependencies, dependency_results) if not result]
        
        if ready_deps:
            logger.info(f"Dependencies ready for {service_name}: {ready_deps}")
        if failed_deps:
            logger.warning(f"Dependencies not available for {service_name}: {failed_deps}")
        
        return True
    
    async def _wait_for_single_dependency(self, service_name: str, dependency: ServiceDependency) -> bool:
        """
        Wait for a single dependency to be ready.
        
        Args:
            service_name: Name of the service waiting
            dependency: The dependency to wait for
            
        Returns:
            True if dependency is ready, False if timeout or failure
        """
        start_time = time.time()
        timeout = dependency.timeout
        
        logger.debug(f"Waiting for dependency {dependency.depends_on} for {service_name} "
                    f"(timeout: {timeout}s, type: {dependency.dependency_type.value})")
        
        while (time.time() - start_time) < timeout:
            # Check if dependency service is ready
            if await self._is_dependency_ready(dependency.depends_on):
                logger.debug(f"Dependency {dependency.depends_on} is ready for {service_name}")
                return True
            
            # Wait before next check
            await asyncio.sleep(dependency.retry_interval)
        
        # Timeout reached
        elapsed = time.time() - start_time
        logger.warning(f"Timeout waiting for dependency {dependency.depends_on} "
                      f"for {service_name} after {elapsed:.1f}s")
        return False
    
    async def _is_dependency_ready(self, service_name: str) -> bool:
        """
        Check if a dependency service is ready.
        
        Args:
            service_name: Name of the service to check
            
        Returns:
            True if service is ready, False otherwise
        """
        if service_name not in self.services:
            # External dependency - assume ready
            logger.debug(f"External dependency {service_name} assumed ready")
            return True
        
        service_info = self.services[service_name]
        return service_info.state == "ready"
    
    async def mark_service_starting(self, service_name: str) -> None:
        """Mark a service as starting."""
        async with self._lock:
            if service_name in self.services:
                service_info = self.services[service_name]
                service_info.state = "starting"
                service_info.startup_time = time.time()
                logger.info(f"Service {service_name} marked as starting")
    
    async def mark_service_ready(self, service_name: str) -> None:
        """Mark a service as ready."""
        async with self._lock:
            if service_name in self.services:
                service_info = self.services[service_name]
                service_info.state = "ready"
                service_info.ready_time = time.time()
                logger.info(f"Service {service_name} marked as ready")
                
                # Log startup time
                if service_info.startup_time:
                    startup_duration = service_info.ready_time - service_info.startup_time
                    logger.info(f"Service {service_name} startup time: {startup_duration:.2f}s")
    
    async def mark_service_failed(self, service_name: str, reason: str = None) -> None:
        """Mark a service as failed."""
        async with self._lock:
            if service_name in self.services:
                service_info = self.services[service_name]
                service_info.state = "failed"
                service_info.failure_reason = reason
                logger.error(f"Service {service_name} marked as failed: {reason}")
    
    def get_service_state(self, service_name: str) -> str:
        """Get the current state of a service."""
        if service_name in self.services:
            return self.services[service_name].state
        return "unknown"
    
    def get_dependent_services(self, service_name: str) -> List[str]:
        """Get list of services that depend on the given service."""
        return self.reverse_graph.get(service_name, [])
    
    def get_ready_services(self) -> List[str]:
        """Get list of services that are currently ready."""
        return [name for name, info in self.services.items() if info.state == "ready"]
    
    def get_failed_services(self) -> List[str]:
        """Get list of services that have failed."""
        return [name for name, info in self.services.items() if info.state == "failed"]
    
    def can_start_service(self, service_name: str) -> Tuple[bool, List[str]]:
        """
        Check if a service can be started based on its dependencies.
        
        Args:
            service_name: Name of the service to check
            
        Returns:
            Tuple of (can_start, missing_dependencies)
        """
        if service_name not in self.services:
            return False, ["Service not registered"]
        
        service_info = self.services[service_name]
        missing_dependencies = []
        
        for dep in service_info.dependencies:
            if dep.dependency_type == DependencyType.REQUIRED:
                if not self._is_dependency_ready_sync(dep.depends_on):
                    missing_dependencies.append(dep.depends_on)
        
        can_start = len(missing_dependencies) == 0
        return can_start, missing_dependencies
    
    def _is_dependency_ready_sync(self, service_name: str) -> bool:
        """Synchronous version of dependency readiness check."""
        if service_name not in self.services:
            return True  # External dependency
        
        return self.services[service_name].state == "ready"
    
    def get_dependency_status(self) -> Dict[str, Dict]:
        """Get comprehensive dependency status for all services."""
        status = {}
        
        for service_name, service_info in self.services.items():
            can_start, missing = self.can_start_service(service_name)
            
            status[service_name] = {
                "state": service_info.state,
                "can_start": can_start,
                "missing_dependencies": missing,
                "startup_time": service_info.startup_time,
                "ready_time": service_info.ready_time,
                "failure_reason": service_info.failure_reason,
                "dependencies": [
                    {
                        "service": dep.depends_on,
                        "type": dep.dependency_type.value,
                        "ready": self._is_dependency_ready_sync(dep.depends_on)
                    }
                    for dep in service_info.dependencies
                ]
            }
        
        return status
    
    def validate_dependencies(self) -> List[str]:
        """
        Validate all dependencies and return any issues found.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Check for circular dependencies
        try:
            self.get_startup_order()
        except ValueError as e:
            errors.append(str(e))
        
        # Check for missing dependency services
        all_service_names = set(self.services.keys())
        for service_name, service_info in self.services.items():
            for dep in service_info.dependencies:
                if dep.depends_on not in all_service_names:
                    # Check if it's an external service (common external services)
                    external_services = {"database", "redis", "postgres", "clickhouse"}
                    if dep.depends_on.lower() not in external_services:
                        errors.append(f"Service {service_name} depends on unknown service {dep.depends_on}")
        
        return errors
    
    def reset_all_states(self) -> None:
        """Reset all service states to pending."""
        for service_info in self.services.values():
            service_info.state = "pending"
            service_info.startup_time = None
            service_info.ready_time = None
            service_info.failure_reason = None
        
        logger.info("All service states reset to pending")
    
    def clear_all(self) -> None:
        """Clear all services and dependencies."""
        self.services.clear()
        self.dependency_graph.clear()
        self.reverse_graph.clear()
        self.startup_order.clear()
        logger.info("All services and dependencies cleared")


def create_default_dependencies() -> List[Tuple[str, List[ServiceDependency]]]:
    """
    Create default service dependencies for the Netra system.
    
    Returns:
        List of tuples (service_name, dependencies)
    """
    return [
        ("database", []),  # Database has no dependencies
        ("redis", []),     # Redis has no dependencies
        ("auth", [
            ServiceDependency("auth", "database", DependencyType.REQUIRED, timeout=30),
            ServiceDependency("auth", "redis", DependencyType.OPTIONAL, timeout=10)
        ]),
        ("backend", [
            ServiceDependency("backend", "database", DependencyType.REQUIRED, timeout=30),
            ServiceDependency("backend", "redis", DependencyType.REQUIRED, timeout=15),
            ServiceDependency("backend", "auth", DependencyType.REQUIRED, timeout=45)
        ]),
        ("frontend", [
            ServiceDependency("frontend", "backend", DependencyType.REQUIRED, timeout=60)
        ]),
        ("websocket", [
            ServiceDependency("websocket", "backend", DependencyType.REQUIRED, timeout=30),
            ServiceDependency("websocket", "redis", DependencyType.REQUIRED, timeout=15)
        ])
    ]


def setup_default_dependency_manager() -> DependencyManager:
    """
    Set up a dependency manager with default Netra service dependencies.
    
    Returns:
        Configured DependencyManager instance
    """
    manager = DependencyManager()
    
    for service_name, dependencies in create_default_dependencies():
        manager.add_service(service_name, dependencies)
    
    # Validate the setup
    errors = manager.validate_dependencies()
    if errors:
        logger.warning(f"Dependency validation warnings: {errors}")
    
    return manager