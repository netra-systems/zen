"""
Enhanced Service Discovery System for Dev Launcher.

Provides comprehensive service discovery with:
- Automatic directory creation and management
- Corruption detection and recovery mechanisms
- Dynamic port allocation with conflict resolution
- Health check validation and monitoring
- Stale registration cleanup with configurable TTL
- Service dependency graph management

Business Value Justification (BVJ):
- Segment: Platform/Internal (Development Infrastructure)
- Business Goal: Development Velocity & Operational Excellence
- Value Impact: Enables reliable multi-service development and testing
- Revenue Impact: Development infrastructure failures slow feature delivery and reduce team productivity
"""
import asyncio
import json
import logging
import os
import shutil
import socket
import time
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

import aiofiles
import aiohttp
import psutil

from dev_launcher.utils import get_logger


class ServiceStatus(Enum):
    """Service discovery status."""
    UNKNOWN = "unknown"
    STARTING = "starting"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class ServiceInfo:
    """Comprehensive service information."""
    name: str
    host: str
    port: int
    protocol: str = "http"
    health_endpoint: str = "/health"
    pid: Optional[int] = None
    start_time: datetime = field(default_factory=datetime.utcnow)
    last_health_check: Optional[datetime] = None
    status: ServiceStatus = ServiceStatus.UNKNOWN
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Runtime tracking
    registration_id: str = field(default_factory=lambda: str(uuid4()))
    health_failures: int = 0
    last_error: Optional[str] = None
    response_time_ms: Optional[float] = None
    
    @property
    def url(self) -> str:
        """Get service base URL."""
        return f"{self.protocol}://{self.host}:{self.port}"
    
    @property
    def health_url(self) -> str:
        """Get service health check URL."""
        return f"{self.url}{self.health_endpoint}"
    
    @property
    def age(self) -> float:
        """Get service age in seconds."""
        return (datetime.utcnow() - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["start_time"] = self.start_time.isoformat()
        data["last_health_check"] = (
            self.last_health_check.isoformat() 
            if self.last_health_check else None
        )
        data["status"] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServiceInfo":
        """Create from dictionary."""
        # Convert datetime fields
        if "start_time" in data and isinstance(data["start_time"], str):
            data["start_time"] = datetime.fromisoformat(data["start_time"])
        if "last_health_check" in data and data["last_health_check"]:
            data["last_health_check"] = datetime.fromisoformat(data["last_health_check"])
        
        # Convert status enum
        if "status" in data:
            data["status"] = ServiceStatus(data["status"])
        
        return cls(**data)


@dataclass 
class PortAllocation:
    """Port allocation information."""
    port: int
    service_name: str
    allocated_at: datetime = field(default_factory=datetime.utcnow)
    reserved: bool = False
    pid: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "port": self.port,
            "service_name": self.service_name,
            "allocated_at": self.allocated_at.isoformat(),
            "reserved": self.reserved,
            "pid": self.pid
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PortAllocation":
        """Create from dictionary."""
        if isinstance(data["allocated_at"], str):
            data["allocated_at"] = datetime.fromisoformat(data["allocated_at"])
        return cls(**data)


class ServiceDiscoveryEnhanced:
    """
    Enhanced service discovery system for development environments.
    
    Features:
    - Automatic service registry management
    - Dynamic port allocation with conflict detection
    - Health monitoring and status tracking
    - Dependency graph validation
    - Corruption detection and recovery
    - Stale registration cleanup
    """
    
    def __init__(self,
                 registry_dir: str = ".netra_services",
                 port_range_start: int = 8000,
                 port_range_end: int = 9000,
                 health_check_interval: float = 30.0,
                 stale_timeout: float = 300.0,  # 5 minutes
                 corruption_check_interval: float = 60.0):
        self.logger = get_logger(__name__)
        
        # Configuration
        self.registry_dir = Path(registry_dir)
        self.port_range_start = port_range_start
        self.port_range_end = port_range_end
        self.health_check_interval = health_check_interval
        self.stale_timeout = stale_timeout
        self.corruption_check_interval = corruption_check_interval
        
        # Registry files
        self.services_file = self.registry_dir / "services.json"
        self.ports_file = self.registry_dir / "ports.json"
        self.dependency_file = self.registry_dir / "dependencies.json"
        
        # In-memory state
        self.services: Dict[str, ServiceInfo] = {}
        self.port_allocations: Dict[int, PortAllocation] = {}
        self.dependency_graph: Dict[str, Set[str]] = {}
        
        # Monitoring tasks
        self.health_monitor_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        self.corruption_check_task: Optional[asyncio.Task] = None
        
        # Locks for thread safety
        self.registry_lock = asyncio.Lock()
        self.port_lock = asyncio.Lock()
        
        self.logger.info("ServiceDiscoveryEnhanced initialized", extra={
            "registry_dir": str(self.registry_dir),
            "port_range": f"{port_range_start}-{port_range_end}",
            "health_check_interval": health_check_interval
        })
    
    async def initialize(self) -> None:
        """Initialize service discovery system."""
        self.logger.info("Initializing service discovery")
        
        # Create registry directory structure
        await self._ensure_registry_directory()
        
        # Load existing registrations
        await self._load_registry_state()
        
        # Validate and clean existing registrations
        await self._validate_existing_services()
        
        # Start monitoring tasks
        await self._start_monitoring_tasks()
        
        self.logger.info("Service discovery initialized", extra={
            "services_count": len(self.services),
            "allocated_ports": len(self.port_allocations)
        })
    
    async def _ensure_registry_directory(self) -> None:
        """Create registry directory structure if it doesn't exist."""
        try:
            self.registry_dir.mkdir(parents=True, exist_ok=True)
            
            # Create lock directory for file-based locking
            lock_dir = self.registry_dir / ".locks"
            lock_dir.mkdir(exist_ok=True)
            
            # Create backup directory for corruption recovery
            backup_dir = self.registry_dir / ".backup"
            backup_dir.mkdir(exist_ok=True)
            
            self.logger.debug("Registry directory structure created", extra={
                "registry_dir": str(self.registry_dir)
            })
            
        except Exception as e:
            self.logger.error("Failed to create registry directory", extra={
                "directory": str(self.registry_dir),
                "error": str(e)
            }, exc_info=True)
            raise
    
    async def _load_registry_state(self) -> None:
        """Load existing registry state from disk."""
        # Load services
        if self.services_file.exists():
            try:
                async with aiofiles.open(self.services_file, 'r') as f:
                    data = json.loads(await f.read())
                    
                for service_data in data.get("services", []):
                    service_info = ServiceInfo.from_dict(service_data)
                    self.services[service_info.name] = service_info
                    
                self.logger.debug("Loaded services from registry", extra={
                    "services_count": len(self.services)
                })
                    
            except Exception as e:
                self.logger.warning("Failed to load services registry", extra={
                    "file": str(self.services_file),
                    "error": str(e)
                })
                await self._backup_corrupted_file(self.services_file)
        
        # Load port allocations
        if self.ports_file.exists():
            try:
                async with aiofiles.open(self.ports_file, 'r') as f:
                    data = json.loads(await f.read())
                    
                for port_data in data.get("ports", []):
                    allocation = PortAllocation.from_dict(port_data)
                    self.port_allocations[allocation.port] = allocation
                    
                self.logger.debug("Loaded port allocations", extra={
                    "ports_count": len(self.port_allocations)
                })
                    
            except Exception as e:
                self.logger.warning("Failed to load port allocations", extra={
                    "file": str(self.ports_file),
                    "error": str(e)
                })
                await self._backup_corrupted_file(self.ports_file)
        
        # Load dependency graph
        if self.dependency_file.exists():
            try:
                async with aiofiles.open(self.dependency_file, 'r') as f:
                    data = json.loads(await f.read())
                    
                for service, deps in data.get("dependencies", {}).items():
                    self.dependency_graph[service] = set(deps)
                    
            except Exception as e:
                self.logger.warning("Failed to load dependency graph", extra={
                    "file": str(self.dependency_file),
                    "error": str(e)
                })
    
    async def _backup_corrupted_file(self, file_path: Path) -> None:
        """Backup a corrupted file for later investigation."""
        try:
            backup_dir = self.registry_dir / ".backup"
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"{file_path.name}.corrupted.{timestamp}"
            
            shutil.copy2(file_path, backup_path)
            file_path.unlink()  # Remove corrupted file
            
            self.logger.info("Backed up corrupted file", extra={
                "original": str(file_path),
                "backup": str(backup_path)
            })
            
        except Exception as e:
            self.logger.error("Failed to backup corrupted file", extra={
                "file": str(file_path),
                "error": str(e)
            })
    
    async def _validate_existing_services(self) -> None:
        """Validate existing service registrations and clean stale ones."""
        stale_services = []
        
        for name, service in self.services.items():
            # Check if process is still running
            if service.pid and not psutil.pid_exists(service.pid):
                stale_services.append(name)
                continue
            
            # Check if port is still in use
            if not await self._is_port_in_use(service.host, service.port):
                stale_services.append(name)
                continue
            
            # Check if service age exceeds stale timeout
            if service.age > self.stale_timeout:
                # Do a health check to confirm staleness
                healthy = await self._check_service_health(service)
                if not healthy:
                    stale_services.append(name)
        
        # Remove stale services
        for name in stale_services:
            await self._unregister_service_internal(name, reason="stale")
        
        if stale_services:
            self.logger.info("Cleaned up stale services", extra={
                "stale_services": stale_services,
                "count": len(stale_services)
            })
    
    async def _start_monitoring_tasks(self) -> None:
        """Start background monitoring tasks."""
        # Health monitoring
        self.health_monitor_task = asyncio.create_task(
            self._health_monitor_loop(),
            name="health-monitor"
        )
        
        # Stale cleanup
        self.cleanup_task = asyncio.create_task(
            self._cleanup_loop(),
            name="stale-cleanup"
        )
        
        # Corruption detection
        self.corruption_check_task = asyncio.create_task(
            self._corruption_check_loop(),
            name="corruption-check"
        )
        
        self.logger.info("Started monitoring tasks")
    
    async def register_service(self,
                             name: str,
                             host: str,
                             port: Optional[int] = None,
                             protocol: str = "http",
                             health_endpoint: str = "/health",
                             pid: Optional[int] = None,
                             dependencies: List[str] = None,
                             metadata: Dict[str, Any] = None) -> ServiceInfo:
        """Register a service with the discovery system."""
        async with self.registry_lock:
            self.logger.info("Registering service", extra={
                "service": name,
                "host": host,
                "requested_port": port
            })
            
            # Allocate port if not provided
            if port is None:
                port = await self.allocate_port(name)
            else:
                # Validate requested port
                await self._validate_and_reserve_port(port, name)
            
            # Validate dependencies
            if dependencies:
                await self._validate_dependencies(name, dependencies)
            
            # Create service info
            service_info = ServiceInfo(
                name=name,
                host=host,
                port=port,
                protocol=protocol,
                health_endpoint=health_endpoint,
                pid=pid,
                dependencies=dependencies or [],
                metadata=metadata or {}
            )
            
            # Register service
            self.services[name] = service_info
            
            # Update dependency graph
            if dependencies:
                self.dependency_graph[name] = set(dependencies)
            
            # Persist changes
            await self._persist_registry_state()
            
            self.logger.info("Service registered successfully", extra={
                "service": name,
                "url": service_info.url,
                "dependencies": dependencies or []
            })
            
            return service_info
    
    async def unregister_service(self, name: str) -> bool:
        """Unregister a service from the discovery system."""
        return await self._unregister_service_internal(name, reason="explicit")
    
    async def _unregister_service_internal(self, name: str, reason: str) -> bool:
        """Internal service unregistration with reason tracking."""
        async with self.registry_lock:
            if name not in self.services:
                return False
            
            service = self.services[name]
            
            self.logger.info("Unregistering service", extra={
                "service": name,
                "reason": reason,
                "port": service.port
            })
            
            # Release port allocation
            if service.port in self.port_allocations:
                del self.port_allocations[service.port]
            
            # Remove from services
            del self.services[name]
            
            # Remove from dependency graph
            self.dependency_graph.pop(name, None)
            
            # Remove dependencies on this service from other services
            for deps in self.dependency_graph.values():
                deps.discard(name)
            
            # Persist changes
            await self._persist_registry_state()
            
            return True
    
    async def allocate_port(self, service_name: str) -> int:
        """Allocate an available port for a service."""
        async with self.port_lock:
            # Find available port in range
            for port in range(self.port_range_start, self.port_range_end + 1):
                if port in self.port_allocations:
                    continue
                
                if await self._is_port_in_use("localhost", port):
                    continue
                
                # Port is available, allocate it
                allocation = PortAllocation(
                    port=port,
                    service_name=service_name
                )
                
                self.port_allocations[port] = allocation
                
                self.logger.debug("Port allocated", extra={
                    "port": port,
                    "service": service_name
                })
                
                return port
            
            # No ports available
            raise RuntimeError(f"No available ports in range {self.port_range_start}-{self.port_range_end}")
    
    async def _validate_and_reserve_port(self, port: int, service_name: str) -> None:
        """Validate and reserve a specific port."""
        if port < self.port_range_start or port > self.port_range_end:
            raise ValueError(f"Port {port} outside allowed range {self.port_range_start}-{self.port_range_end}")
        
        if port in self.port_allocations:
            existing = self.port_allocations[port]
            if existing.service_name != service_name:
                raise ValueError(f"Port {port} already allocated to service {existing.service_name}")
        
        if await self._is_port_in_use("localhost", port):
            raise ValueError(f"Port {port} is already in use")
        
        # Reserve the port
        self.port_allocations[port] = PortAllocation(
            port=port,
            service_name=service_name,
            reserved=True
        )
    
    async def _is_port_in_use(self, host: str, port: int) -> bool:
        """Check if a port is currently in use."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                return result == 0
        except Exception:
            return False
    
    async def _validate_dependencies(self, service_name: str, dependencies: List[str]) -> None:
        """Validate service dependencies."""
        missing_deps = []
        for dep in dependencies:
            if dep not in self.services:
                missing_deps.append(dep)
        
        if missing_deps:
            self.logger.warning("Service has missing dependencies", extra={
                "service": service_name,
                "missing_dependencies": missing_deps
            })
            # Don't raise error - dependencies might be registered later
    
    async def get_service(self, name: str) -> Optional[ServiceInfo]:
        """Get service information by name."""
        return self.services.get(name)
    
    async def list_services(self, status_filter: Optional[ServiceStatus] = None) -> List[ServiceInfo]:
        """List all services, optionally filtered by status."""
        services = list(self.services.values())
        
        if status_filter:
            services = [s for s in services if s.status == status_filter]
        
        return services
    
    async def get_service_dependencies(self, service_name: str) -> List[str]:
        """Get dependencies for a service."""
        service = self.services.get(service_name)
        return service.dependencies if service else []
    
    async def get_dependents(self, service_name: str) -> List[str]:
        """Get services that depend on the given service."""
        dependents = []
        for name, deps in self.dependency_graph.items():
            if service_name in deps:
                dependents.append(name)
        return dependents
    
    async def validate_startup_order(self) -> List[str]:
        """Get valid service startup order based on dependencies."""
        # Topological sort of dependency graph
        in_degree = {name: 0 for name in self.services}
        
        # Calculate in-degrees
        for service_deps in self.dependency_graph.values():
            for dep in service_deps:
                if dep in in_degree:
                    in_degree[dep] += 1
        
        # Topological sort
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            # Reduce in-degree for dependent services
            for name, deps in self.dependency_graph.items():
                if current in deps:
                    in_degree[name] -= 1
                    if in_degree[name] == 0:
                        queue.append(name)
        
        if len(result) != len(self.services):
            # Circular dependency detected
            remaining = set(self.services.keys()) - set(result)
            self.logger.error("Circular dependency detected", extra={
                "remaining_services": list(remaining)
            })
            raise ValueError(f"Circular dependency detected in services: {remaining}")
        
        return result
    
    async def _persist_registry_state(self) -> None:
        """Persist current registry state to disk."""
        try:
            # Services
            services_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "services": [service.to_dict() for service in self.services.values()]
            }
            
            async with aiofiles.open(self.services_file, 'w') as f:
                await f.write(json.dumps(services_data, indent=2))
            
            # Port allocations
            ports_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "ports": [allocation.to_dict() for allocation in self.port_allocations.values()]
            }
            
            async with aiofiles.open(self.ports_file, 'w') as f:
                await f.write(json.dumps(ports_data, indent=2))
            
            # Dependencies
            dependencies_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "dependencies": {name: list(deps) for name, deps in self.dependency_graph.items()}
            }
            
            async with aiofiles.open(self.dependency_file, 'w') as f:
                await f.write(json.dumps(dependencies_data, indent=2))
            
        except Exception as e:
            self.logger.error("Failed to persist registry state", extra={
                "error": str(e)
            }, exc_info=True)
    
    async def _health_monitor_loop(self) -> None:
        """Background task for health monitoring."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                # Check health of all registered services
                for service in self.services.values():
                    await self._update_service_health(service)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in health monitor loop", extra={
                    "error": str(e)
                }, exc_info=True)
    
    async def _update_service_health(self, service: ServiceInfo) -> None:
        """Update health status for a single service."""
        try:
            healthy = await self._check_service_health(service)
            
            if healthy:
                service.status = ServiceStatus.HEALTHY
                service.health_failures = 0
                service.last_error = None
            else:
                service.health_failures += 1
                service.status = ServiceStatus.UNHEALTHY
                
                # If too many failures, mark as stopped
                if service.health_failures >= 3:
                    service.status = ServiceStatus.STOPPED
            
            service.last_health_check = datetime.utcnow()
            
        except Exception as e:
            service.status = ServiceStatus.UNHEALTHY
            service.health_failures += 1
            service.last_error = str(e)
            service.last_health_check = datetime.utcnow()
    
    async def _check_service_health(self, service: ServiceInfo) -> bool:
        """Perform health check for a service."""
        try:
            start_time = time.time()
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(service.health_url) as response:
                    response_time = (time.time() - start_time) * 1000
                    service.response_time_ms = response_time
                    
                    return response.status == 200
                    
        except Exception as e:
            self.logger.debug("Health check failed", extra={
                "service": service.name,
                "url": service.health_url,
                "error": str(e)
            })
            return False
    
    async def _cleanup_loop(self) -> None:
        """Background task for cleaning up stale registrations."""
        while True:
            try:
                await asyncio.sleep(60)  # Run cleanup every minute
                
                await self._validate_existing_services()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in cleanup loop", extra={
                    "error": str(e)
                }, exc_info=True)
    
    async def _corruption_check_loop(self) -> None:
        """Background task for checking registry corruption."""
        while True:
            try:
                await asyncio.sleep(self.corruption_check_interval)
                
                # Check file integrity
                await self._check_registry_integrity()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in corruption check loop", extra={
                    "error": str(e)
                }, exc_info=True)
    
    async def _check_registry_integrity(self) -> None:
        """Check registry file integrity and fix corruption."""
        registry_files = [self.services_file, self.ports_file, self.dependency_file]
        
        for file_path in registry_files:
            if not file_path.exists():
                continue
            
            try:
                # Try to parse the file
                async with aiofiles.open(file_path, 'r') as f:
                    json.loads(await f.read())
                    
            except json.JSONDecodeError:
                self.logger.warning("Corrupted registry file detected", extra={
                    "file": str(file_path)
                })
                
                # Backup corrupted file and recreate
                await self._backup_corrupted_file(file_path)
                
                # Recreate with current in-memory state
                await self._persist_registry_state()
    
    async def cleanup(self) -> None:
        """Clean up service discovery system."""
        self.logger.info("Cleaning up service discovery")
        
        # Cancel monitoring tasks
        for task in [self.health_monitor_task, self.cleanup_task, self.corruption_check_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Final persistence
        await self._persist_registry_state()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        healthy_services = sum(1 for s in self.services.values() if s.status == ServiceStatus.HEALTHY)
        
        return {
            "services_total": len(self.services),
            "services_healthy": healthy_services,
            "services_unhealthy": len(self.services) - healthy_services,
            "ports_allocated": len(self.port_allocations),
            "port_range": f"{self.port_range_start}-{self.port_range_end}",
            "dependency_graph_size": len(self.dependency_graph),
            "registry_directory": str(self.registry_dir),
            "monitoring_active": self.health_monitor_task is not None and not self.health_monitor_task.done()
        }


# Global enhanced service discovery instance
service_discovery = ServiceDiscoveryEnhanced()