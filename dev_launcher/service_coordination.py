"""
Service Coordination Module - Initialization Gates and Platform-Aware Port Allocation
Business Value: Ensures reliable service startup and prevents port conflicts
"""

import asyncio
import platform
import socket
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import logging
import random

from dev_launcher.isolated_environment import get_env

logger = logging.getLogger(__name__)


class ServiceState(Enum):
    """Service lifecycle states."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    WAITING_DEPENDENCIES = "waiting_dependencies"
    READY = "ready"
    FAILED = "failed"
    STOPPING = "stopping"
    STOPPED = "stopped"


class PortAllocationStrategy(Enum):
    """Port allocation strategies for different platforms."""
    DYNAMIC = "dynamic"  # Dynamic port allocation
    STATIC = "static"    # Static port allocation
    EPHEMERAL = "ephemeral"  # OS-assigned ephemeral ports


@dataclass
class ServiceDependency:
    """Represents a service dependency."""
    service_name: str
    required: bool = True
    health_check_endpoint: Optional[str] = None
    timeout: float = 30.0


@dataclass
class ServiceInitGate:
    """Initialization gate for service coordination."""
    service_name: str
    state: ServiceState = ServiceState.UNINITIALIZED
    dependencies: List[ServiceDependency] = field(default_factory=list)
    health_check_endpoint: Optional[str] = None
    init_start_time: Optional[float] = None
    init_end_time: Optional[float] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


class PlatformAwarePortAllocator:
    """Platform-aware port allocation with conflict resolution."""
    
    # Platform-specific port ranges
    PLATFORM_PORT_RANGES = {
        "Windows": (49152, 65535),  # Windows dynamic port range
        "Darwin": (49152, 65535),   # macOS dynamic port range  
        "Linux": (32768, 60999),     # Linux default ephemeral range
    }
    
    # Service-specific preferred ports
    SERVICE_PREFERRED_PORTS = {
        "backend": [8000, 8001, 8002],
        "auth": [8080, 8081, 8082],
        "frontend": [3000, 3001, 3002],
        "redis": [6379, 6380, 6381],
        "postgres": [5432, 5433, 5434],
        "clickhouse": [8123, 8124, 9000],
    }
    
    def __init__(self):
        """Initialize the port allocator."""
        self.allocated_ports: Set[int] = set()
        self.service_port_map: Dict[str, int] = {}
        self.platform_name = platform.system()
        self._lock = asyncio.Lock()
    
    async def allocate_port(
        self, 
        service_name: str,
        preferred_port: Optional[int] = None,
        strategy: PortAllocationStrategy = PortAllocationStrategy.DYNAMIC
    ) -> int:
        """
        Allocate a port for a service with platform awareness.
        
        Args:
            service_name: Name of the service
            preferred_port: Preferred port if available
            strategy: Port allocation strategy
            
        Returns:
            Allocated port number
        """
        async with self._lock:
            # Check if service already has a port
            if service_name in self.service_port_map:
                return self.service_port_map[service_name]
            
            # Try preferred port first
            if preferred_port and self._is_port_available(preferred_port):
                return await self._assign_port(service_name, preferred_port)
            
            # Try service-specific preferred ports
            if service_name in self.SERVICE_PREFERRED_PORTS:
                for port in self.SERVICE_PREFERRED_PORTS[service_name]:
                    if self._is_port_available(port):
                        return await self._assign_port(service_name, port)
            
            # Use platform-specific strategy
            if strategy == PortAllocationStrategy.EPHEMERAL:
                port = self._get_ephemeral_port()
                return await self._assign_port(service_name, port)
            elif strategy == PortAllocationStrategy.DYNAMIC:
                port = await self._find_dynamic_port()
                return await self._assign_port(service_name, port)
            else:
                # Static strategy - fail if preferred port not available
                raise ValueError(f"No available port for {service_name} with static strategy")
    
    async def release_port(self, service_name: str):
        """Release a port allocated to a service."""
        async with self._lock:
            if service_name in self.service_port_map:
                port = self.service_port_map[service_name]
                self.allocated_ports.discard(port)
                del self.service_port_map[service_name]
                logger.info(f"Released port {port} for service {service_name}")
    
    def _is_port_available(self, port: int) -> bool:
        """
        Check if a port is available for binding.
        
        Args:
            port: Port number to check
            
        Returns:
            True if port is available
        """
        if port in self.allocated_ports:
            return False
        
        try:
            # Platform-specific socket options
            if self.platform_name == "Windows":
                # Windows-specific socket handling
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            else:
                # Unix-like systems
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            sock.settimeout(1)
            sock.bind(('127.0.0.1', port))
            sock.close()
            return True
        except (OSError, socket.error) as e:
            logger.debug(f"Port {port} not available: {e}")
            return False
    
    def _get_ephemeral_port(self) -> int:
        """Get an ephemeral port assigned by the OS."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('', 0))
        port = sock.getsockname()[1]
        sock.close()
        return port
    
    async def _find_dynamic_port(self) -> int:
        """
        Find an available port in the platform-specific dynamic range.
        
        Returns:
            Available port number
        """
        min_port, max_port = self.PLATFORM_PORT_RANGES.get(
            self.platform_name, 
            (49152, 65535)  # Default fallback
        )
        
        # Try random ports with exponential backoff
        max_attempts = 100
        for attempt in range(max_attempts):
            port = random.randint(min_port, max_port)
            if self._is_port_available(port):
                return port
            
            # Exponential backoff with jitter
            if attempt < max_attempts - 1:
                await asyncio.sleep(0.01 * (2 ** min(attempt, 5)) + random.random() * 0.01)
        
        # Last resort: get ephemeral port
        logger.warning(f"Could not find dynamic port after {max_attempts} attempts, using ephemeral")
        return self._get_ephemeral_port()
    
    async def _assign_port(self, service_name: str, port: int) -> int:
        """Assign a port to a service."""
        self.allocated_ports.add(port)
        self.service_port_map[service_name] = port
        logger.info(f"Allocated port {port} for service {service_name} on {self.platform_name}")
        return port
    
    def get_allocation_summary(self) -> Dict[str, any]:
        """Get summary of port allocations."""
        return {
            "platform": self.platform_name,
            "allocated_ports": len(self.allocated_ports),
            "service_ports": dict(self.service_port_map),
            "port_range": self.PLATFORM_PORT_RANGES.get(self.platform_name, "default")
        }


class ServiceCoordinator:
    """
    Coordinates service initialization with dependency gates.
    """
    
    def __init__(self, port_allocator: Optional[PlatformAwarePortAllocator] = None):
        """Initialize the service coordinator."""
        self.services: Dict[str, ServiceInitGate] = {}
        self.port_allocator = port_allocator or PlatformAwarePortAllocator()
        self._initialization_order: List[str] = []
        self._lock = asyncio.Lock()
    
    async def register_service(
        self, 
        service_name: str,
        dependencies: Optional[List[ServiceDependency]] = None,
        health_check_endpoint: Optional[str] = None
    ) -> ServiceInitGate:
        """
        Register a service with its dependencies.
        
        Args:
            service_name: Name of the service
            dependencies: List of service dependencies
            health_check_endpoint: Health check endpoint
            
        Returns:
            ServiceInitGate for the service
        """
        async with self._lock:
            if service_name in self.services:
                return self.services[service_name]
            
            gate = ServiceInitGate(
                service_name=service_name,
                dependencies=dependencies or [],
                health_check_endpoint=health_check_endpoint
            )
            self.services[service_name] = gate
            logger.info(f"Registered service {service_name} with {len(gate.dependencies)} dependencies")
            return gate
    
    async def initialize_service(
        self, 
        service_name: str,
        port_config: Optional[Dict] = None
    ) -> Tuple[bool, Optional[int]]:
        """
        Initialize a service with dependency checking and port allocation.
        
        Args:
            service_name: Name of the service to initialize
            port_config: Port configuration (preferred_port, strategy)
            
        Returns:
            Tuple of (success, allocated_port)
        """
        if service_name not in self.services:
            logger.error(f"Service {service_name} not registered")
            return False, None
        
        gate = self.services[service_name]
        
        # Check if already initialized
        if gate.state == ServiceState.READY:
            port = self.port_allocator.service_port_map.get(service_name)
            return True, port
        
        # Mark as initializing
        async with self._lock:
            gate.state = ServiceState.INITIALIZING
            gate.init_start_time = time.time()
        
        try:
            # Wait for dependencies
            if not await self._wait_for_dependencies(gate):
                gate.state = ServiceState.FAILED
                gate.error_message = "Dependencies failed to initialize"
                return False, None
            
            # Allocate port
            port_config = port_config or {}
            port = await self.port_allocator.allocate_port(
                service_name,
                preferred_port=port_config.get('preferred_port'),
                strategy=PortAllocationStrategy(
                    port_config.get('strategy', 'dynamic')
                )
            )
            
            # Mark as ready
            async with self._lock:
                gate.state = ServiceState.READY
                gate.init_end_time = time.time()
                self._initialization_order.append(service_name)
            
            init_time = gate.init_end_time - gate.init_start_time
            logger.info(f"Service {service_name} initialized in {init_time:.2f}s on port {port}")
            return True, port
            
        except Exception as e:
            logger.error(f"Failed to initialize {service_name}: {e}")
            async with self._lock:
                gate.state = ServiceState.FAILED
                gate.error_message = str(e)
                gate.retry_count += 1
            return False, None
    
    async def _wait_for_dependencies(
        self, 
        gate: ServiceInitGate,
        timeout: float = 60.0
    ) -> bool:
        """
        Wait for service dependencies to be ready.
        
        Args:
            gate: Service initialization gate
            timeout: Maximum wait time
            
        Returns:
            True if all dependencies are ready
        """
        if not gate.dependencies:
            return True
        
        gate.state = ServiceState.WAITING_DEPENDENCIES
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            all_ready = True
            failed_deps = []
            
            for dep in gate.dependencies:
                if dep.service_name not in self.services:
                    if dep.required:
                        logger.error(f"Required dependency {dep.service_name} not registered")
                        return False
                    continue
                
                dep_gate = self.services[dep.service_name]
                if dep_gate.state != ServiceState.READY:
                    all_ready = False
                    if dep_gate.state == ServiceState.FAILED and dep.required:
                        failed_deps.append(dep.service_name)
            
            if failed_deps:
                logger.error(f"Required dependencies failed: {failed_deps}")
                return False
            
            if all_ready:
                return True
            
            await asyncio.sleep(0.5)
        
        logger.error(f"Timeout waiting for dependencies of {gate.service_name}")
        return False
    
    async def stop_service(self, service_name: str):
        """Stop a service and release its resources."""
        if service_name not in self.services:
            return
        
        async with self._lock:
            gate = self.services[service_name]
            gate.state = ServiceState.STOPPING
        
        # Release allocated port
        await self.port_allocator.release_port(service_name)
        
        async with self._lock:
            gate.state = ServiceState.STOPPED
        
        logger.info(f"Service {service_name} stopped")
    
    async def stop_all_services(self):
        """Stop all services in reverse initialization order."""
        for service_name in reversed(self._initialization_order):
            await self.stop_service(service_name)
    
    def get_initialization_summary(self) -> Dict[str, any]:
        """Get summary of service initialization."""
        summary = {
            "total_services": len(self.services),
            "ready": 0,
            "failed": 0,
            "pending": 0,
            "services": {},
            "initialization_order": self._initialization_order,
            "port_allocation": self.port_allocator.get_allocation_summary()
        }
        
        for name, gate in self.services.items():
            if gate.state == ServiceState.READY:
                summary["ready"] += 1
            elif gate.state == ServiceState.FAILED:
                summary["failed"] += 1
            else:
                summary["pending"] += 1
            
            summary["services"][name] = {
                "state": gate.state.value,
                "dependencies": [d.service_name for d in gate.dependencies],
                "init_time": (gate.init_end_time - gate.init_start_time) 
                           if gate.init_end_time and gate.init_start_time else None,
                "error": gate.error_message,
                "retries": gate.retry_count
            }
        
        return summary


# Global coordinator instance
_coordinator: Optional[ServiceCoordinator] = None


def get_service_coordinator() -> ServiceCoordinator:
    """Get or create the global service coordinator."""
    global _coordinator
    if _coordinator is None:
        _coordinator = ServiceCoordinator()
    return _coordinator


async def initialize_services_with_gates(
    services: List[Dict],
    parallel: bool = True
) -> Dict[str, any]:
    """
    Initialize multiple services with dependency gates.
    
    Args:
        services: List of service configurations
        parallel: Whether to initialize in parallel where possible
        
    Returns:
        Initialization summary
    """
    coordinator = get_service_coordinator()
    
    # Register all services first
    for service_config in services:
        dependencies = []
        for dep_name in service_config.get('depends_on', []):
            dependencies.append(ServiceDependency(
                service_name=dep_name,
                required=True
            ))
        
        await coordinator.register_service(
            service_name=service_config['name'],
            dependencies=dependencies,
            health_check_endpoint=service_config.get('health_endpoint')
        )
    
    # Initialize services
    if parallel:
        # Initialize in parallel where possible
        tasks = []
        for service_config in services:
            task = asyncio.create_task(
                coordinator.initialize_service(
                    service_config['name'],
                    port_config=service_config.get('port_config')
                )
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Service {services[i]['name']} failed: {result}")
    else:
        # Initialize sequentially
        for service_config in services:
            await coordinator.initialize_service(
                service_config['name'],
                port_config=service_config.get('port_config')
            )
    
    return coordinator.get_initialization_summary()