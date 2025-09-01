"""
Dynamic Port Allocator for Test Framework

Provides dynamic port allocation with conflict detection and cleanup for parallel test execution.
Ensures each test environment gets unique ports to prevent conflicts.

Business Value Justification (BVJ):
1. Segment: Platform/Internal - Development Velocity, Risk Reduction
2. Business Goal: Enable truly parallel test execution without port conflicts
3. Value Impact: Prevents test flakiness, enables CI/CD scaling, reduces developer downtime
4. Strategic Impact: Enables running multiple test suites simultaneously, improves CI throughput
"""

import socket
import logging
import os
import json
import threading
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager
from datetime import datetime, timedelta
from enum import Enum

# CLAUDE.md compliance: Use IsolatedEnvironment for all environment access
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class PortRange(Enum):
    """Port ranges for different environment types."""
    # Development ports (standard)
    DEVELOPMENT = (8000, 8999)
    
    # Shared test environment
    SHARED_TEST = (30000, 30999)
    
    # Dedicated test environments
    DEDICATED_TEST = (31000, 39999)
    
    # CI/CD environments
    CI_CD = (40000, 49999)
    
    # Staging environments
    STAGING = (50000, 59999)


@dataclass
class PortAllocation:
    """Represents a port allocation for a service."""
    service_name: str
    port: int
    environment_id: str
    allocated_at: datetime
    test_id: Optional[str] = None
    process_id: Optional[int] = None
    is_locked: bool = False
    
    def is_expired(self, max_age_hours: float = 24) -> bool:
        """Check if allocation is expired."""
        age = datetime.now() - self.allocated_at
        return age.total_seconds() / 3600 > max_age_hours


@dataclass
class ServicePortConfig:
    """Configuration for service port requirements."""
    service_name: str
    base_port: int  # Default/preferred port
    port_offset: int = 0  # Offset from base for this service
    protocol: str = "tcp"
    requires_sequential: bool = False  # If true, allocate sequential ports
    
    
@dataclass 
class PortAllocationResult:
    """Result of port allocation attempt."""
    success: bool
    ports: Dict[str, int] = field(default_factory=dict)
    environment_id: str = ""
    error_message: Optional[str] = None
    retry_after: Optional[float] = None  # Seconds to wait before retry


class DynamicPortAllocator:
    """
    Dynamic port allocator with conflict detection and cleanup.
    
    Single Source of Truth (SSOT) for port allocation in test environments.
    Provides OS-level port binding verification and persistent allocation tracking.
    """
    
    # Class-level configuration
    STATE_DIR = Path("/tmp/netra_port_state") if os.name != 'nt' else Path(os.environ.get('TEMP', '.')) / "netra_port_state"
    STATE_FILE = STATE_DIR / "port_allocations.json"
    LOCK_FILE = STATE_DIR / "port_allocator.lock"
    
    # Allocation configuration
    MAX_RETRY_ATTEMPTS = 10
    PORT_CHECK_TIMEOUT = 1.0  # seconds
    CLEANUP_AGE_HOURS = 24  # Clean up allocations older than this
    
    # Service configurations with base ports
    SERVICE_CONFIGS = {
        "backend": ServicePortConfig("backend", 8000, 0),
        "auth": ServicePortConfig("auth", 8001, 1),
        "frontend": ServicePortConfig("frontend", 3000, 1000),  # Different range
        "postgres": ServicePortConfig("postgres", 5432, 2000),
        "redis": ServicePortConfig("redis", 6379, 2100),
        "clickhouse": ServicePortConfig("clickhouse", 8123, 2200),
    }
    
    def __init__(self, 
                 port_range: PortRange = PortRange.SHARED_TEST,
                 environment_id: Optional[str] = None,
                 test_id: Optional[str] = None):
        """
        Initialize dynamic port allocator.
        
        Args:
            port_range: Port range to allocate from
            environment_id: Unique environment identifier
            test_id: Optional test identifier for tracking
        """
        self.port_range = port_range
        self.environment_id = environment_id or self._generate_environment_id()
        self.test_id = test_id
        self.process_id = os.getpid()
        
        # Thread-local storage for locks
        self._local = threading.local()
        
        # In-memory cache of allocations
        self._allocations: Dict[str, PortAllocation] = {}
        self._allocated_ports: Set[int] = set()
        
        # Initialize state directory
        self.STATE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Load existing allocations
        self._load_state()
        
    def _generate_environment_id(self) -> str:
        """Generate unique environment ID."""
        timestamp = datetime.now().isoformat()
        pid = os.getpid()
        hostname = socket.gethostname()
        return hashlib.md5(f"{hostname}_{pid}_{timestamp}".encode()).hexdigest()[:12]
    
    @contextmanager
    def _file_lock(self, timeout: float = 30):
        """Cross-platform file locking for state persistence."""
        if os.name != 'nt':
            import fcntl
        else:
            fcntl = None
        
        if os.name == 'nt':
            import msvcrt
        else:
            msvcrt = None
        
        self.LOCK_FILE.touch(exist_ok=True)
        start_time = time.time()
        locked = False
        
        with open(self.LOCK_FILE, 'r+') as f:
            while time.time() - start_time < timeout:
                try:
                    if os.name == 'nt':
                        # Windows locking
                        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        # Unix locking
                        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                    break
                except (IOError, OSError):
                    time.sleep(0.1)
            
            if not locked:
                raise TimeoutError(f"Could not acquire lock within {timeout} seconds")
            
            try:
                yield
            finally:
                if os.name == 'nt':
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(f, fcntl.LOCK_UN)
    
    def _load_state(self) -> None:
        """Load persisted allocation state."""
        try:
            if self.STATE_FILE.exists():
                with self._file_lock():
                    with open(self.STATE_FILE, 'r') as f:
                        state = json.load(f)
                        
                    # Convert to PortAllocation objects
                    for env_id, allocations in state.get("allocations", {}).items():
                        for service, alloc_data in allocations.items():
                            allocation = PortAllocation(
                                service_name=alloc_data["service_name"],
                                port=alloc_data["port"],
                                environment_id=alloc_data["environment_id"],
                                allocated_at=datetime.fromisoformat(alloc_data["allocated_at"]),
                                test_id=alloc_data.get("test_id"),
                                process_id=alloc_data.get("process_id"),
                                is_locked=alloc_data.get("is_locked", False)
                            )
                            
                            # Only load if not expired
                            if not allocation.is_expired(self.CLEANUP_AGE_HOURS):
                                # Load all allocations to track used ports
                                self._allocated_ports.add(allocation.port)
                                
                                # Only load allocations for our environment
                                if env_id == self.environment_id:
                                    key = f"{env_id}_{service}"
                                    self._allocations[key] = allocation
                                
        except Exception as e:
            logger.warning(f"Could not load allocation state: {e}")
    
    def _save_state(self) -> None:
        """Persist allocation state."""
        try:
            with self._file_lock():
                # Group allocations by environment
                state = {"allocations": {}}
                
                for key, allocation in self._allocations.items():
                    env_id = allocation.environment_id
                    if env_id not in state["allocations"]:
                        state["allocations"][env_id] = {}
                    
                    state["allocations"][env_id][allocation.service_name] = {
                        "service_name": allocation.service_name,
                        "port": allocation.port,
                        "environment_id": allocation.environment_id,
                        "allocated_at": allocation.allocated_at.isoformat(),
                        "test_id": allocation.test_id,
                        "process_id": allocation.process_id,
                        "is_locked": allocation.is_locked
                    }
                
                with open(self.STATE_FILE, 'w') as f:
                    json.dump(state, f, indent=2)
                    
        except Exception as e:
            logger.error(f"Could not save allocation state: {e}")
    
    def is_port_available(self, port: int, host: str = "127.0.0.1") -> bool:
        """
        Check if a port is available using OS-level binding test.
        
        Args:
            port: Port number to check
            host: Host to bind to
            
        Returns:
            True if port is available
        """
        try:
            # Try to bind to the port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.settimeout(self.PORT_CHECK_TIMEOUT)
                sock.bind((host, port))
                return True
        except (OSError, socket.error):
            return False
    
    def _find_available_port(self, 
                            start_port: int, 
                            end_port: int,
                            excluded_ports: Optional[Set[int]] = None) -> Optional[int]:
        """
        Find an available port in the given range.
        
        Args:
            start_port: Start of port range
            end_port: End of port range
            excluded_ports: Ports to exclude from search
            
        Returns:
            Available port number or None
        """
        excluded = excluded_ports or set()
        excluded.update(self._allocated_ports)
        
        # Try random ports first for better distribution
        import random
        ports_to_try = list(range(start_port, end_port + 1))
        random.shuffle(ports_to_try)
        
        for port in ports_to_try:
            if port in excluded:
                continue
                
            if self.is_port_available(port):
                return port
        
        return None
    
    def allocate_ports(self, 
                       services: List[str],
                       prefer_sequential: bool = False) -> PortAllocationResult:
        """
        Allocate ports for multiple services.
        
        Args:
            services: List of service names
            prefer_sequential: Try to allocate sequential ports
            
        Returns:
            PortAllocationResult with allocated ports
        """
        logger.info(f"Allocating ports for {len(services)} services in environment {self.environment_id}")
        
        # Check for existing allocations
        existing_ports = {}
        for service in services:
            key = f"{self.environment_id}_{service}"
            if key in self._allocations:
                allocation = self._allocations[key]
                # Verify the port is still available
                if self.is_port_available(allocation.port):
                    existing_ports[service] = allocation.port
                    logger.info(f"Reusing existing allocation for {service}: port {allocation.port}")
                else:
                    # Port no longer available, remove allocation
                    logger.warning(f"Previously allocated port {allocation.port} for {service} is no longer available")
                    del self._allocations[key]
                    self._allocated_ports.discard(allocation.port)
        
        # Allocate new ports for services without allocations
        new_ports = {}
        failed_services = []
        
        start_port, end_port = self.port_range.value
        
        for service in services:
            if service in existing_ports:
                new_ports[service] = existing_ports[service]
                continue
            
            # Get service configuration
            config = self.SERVICE_CONFIGS.get(service)
            if not config:
                logger.warning(f"No configuration for service {service}, using defaults")
                config = ServicePortConfig(service, start_port, 0)
            
            # Calculate preferred port based on offset
            preferred_port = start_port + config.port_offset
            
            # Try to allocate port
            allocated_port = None
            
            # Build set of already used ports (including globally allocated ones)
            used_ports = self._allocated_ports.copy()
            used_ports.update(new_ports.values())
            
            # First try preferred port
            if preferred_port >= start_port and preferred_port <= end_port:
                if preferred_port not in used_ports and self.is_port_available(preferred_port):
                    allocated_port = preferred_port
            
            # If preferred not available, find any available port
            if not allocated_port:
                allocated_port = self._find_available_port(
                    start_port, 
                    end_port,
                    excluded_ports=used_ports
                )
            
            if allocated_port:
                # Create allocation
                allocation = PortAllocation(
                    service_name=service,
                    port=allocated_port,
                    environment_id=self.environment_id,
                    allocated_at=datetime.now(),
                    test_id=self.test_id,
                    process_id=self.process_id
                )
                
                key = f"{self.environment_id}_{service}"
                self._allocations[key] = allocation
                self._allocated_ports.add(allocated_port)
                new_ports[service] = allocated_port
                
                logger.info(f"Allocated port {allocated_port} for {service}")
            else:
                failed_services.append(service)
                logger.error(f"Failed to allocate port for {service}")
        
        # Save state
        self._save_state()
        
        # Build result
        if failed_services:
            return PortAllocationResult(
                success=False,
                ports=new_ports,
                environment_id=self.environment_id,
                error_message=f"Failed to allocate ports for: {', '.join(failed_services)}",
                retry_after=5.0
            )
        
        return PortAllocationResult(
            success=True,
            ports=new_ports,
            environment_id=self.environment_id
        )
    
    def release_ports(self, services: Optional[List[str]] = None) -> None:
        """
        Release allocated ports.
        
        Args:
            services: Services to release ports for, None for all
        """
        if services is None:
            # Release all ports for this environment
            services = [
                alloc.service_name 
                for key, alloc in self._allocations.items() 
                if alloc.environment_id == self.environment_id
            ]
        
        for service in services:
            key = f"{self.environment_id}_{service}"
            if key in self._allocations:
                allocation = self._allocations[key]
                self._allocated_ports.discard(allocation.port)
                del self._allocations[key]
                logger.info(f"Released port {allocation.port} for {service}")
        
        self._save_state()
    
    def cleanup_expired_allocations(self, max_age_hours: Optional[float] = None) -> int:
        """
        Clean up expired port allocations.
        
        Args:
            max_age_hours: Maximum age in hours, uses default if None
            
        Returns:
            Number of allocations cleaned up
        """
        max_age = max_age_hours or self.CLEANUP_AGE_HOURS
        cleaned = 0
        
        # Find expired allocations
        expired_keys = []
        for key, allocation in self._allocations.items():
            if allocation.is_expired(max_age):
                # Also check if process is still running
                if allocation.process_id and allocation.process_id != self.process_id:
                    try:
                        # Check if process exists (Unix/Windows compatible)
                        os.kill(allocation.process_id, 0)
                        # Process exists, check if port is actually in use
                        if not self.is_port_available(allocation.port):
                            continue  # Don't clean up, still in use
                    except (OSError, ProcessLookupError):
                        # Process doesn't exist, safe to clean up
                        pass
                
                expired_keys.append(key)
        
        # Clean up expired allocations
        for key in expired_keys:
            allocation = self._allocations[key]
            self._allocated_ports.discard(allocation.port)
            del self._allocations[key]
            cleaned += 1
            logger.info(f"Cleaned up expired allocation: {allocation.service_name} port {allocation.port}")
        
        if cleaned > 0:
            self._save_state()
        
        return cleaned
    
    def get_allocation_stats(self) -> Dict[str, any]:
        """Get statistics about current allocations."""
        stats = {
            "total_allocations": len(self._allocations),
            "environments": {},
            "port_ranges": {},
            "services": {}
        }
        
        # Group by environment
        for allocation in self._allocations.values():
            env_id = allocation.environment_id
            if env_id not in stats["environments"]:
                stats["environments"][env_id] = {
                    "services": [],
                    "ports": [],
                    "test_id": allocation.test_id,
                    "process_id": allocation.process_id,
                    "age_hours": (datetime.now() - allocation.allocated_at).total_seconds() / 3600
                }
            stats["environments"][env_id]["services"].append(allocation.service_name)
            stats["environments"][env_id]["ports"].append(allocation.port)
        
        # Port range usage
        for range_name, (start, end) in [(r.name, r.value) for r in PortRange]:
            used = sum(1 for p in self._allocated_ports if start <= p <= end)
            total = end - start + 1
            stats["port_ranges"][range_name] = {
                "used": used,
                "total": total,
                "percentage": (used / total) * 100 if total > 0 else 0
            }
        
        # Service allocation counts
        for allocation in self._allocations.values():
            service = allocation.service_name
            if service not in stats["services"]:
                stats["services"][service] = 0
            stats["services"][service] += 1
        
        return stats
    
    def lock_allocation(self, service: str) -> bool:
        """
        Lock an allocation to prevent cleanup.
        
        Args:
            service: Service name to lock
            
        Returns:
            True if locked successfully
        """
        key = f"{self.environment_id}_{service}"
        if key in self._allocations:
            self._allocations[key].is_locked = True
            self._save_state()
            return True
        return False
    
    def unlock_allocation(self, service: str) -> bool:
        """
        Unlock an allocation.
        
        Args:
            service: Service name to unlock
            
        Returns:
            True if unlocked successfully
        """
        key = f"{self.environment_id}_{service}"
        if key in self._allocations:
            self._allocations[key].is_locked = False
            self._save_state()
            return True
        return False
    
    def get_service_port(self, service: str) -> Optional[int]:
        """
        Get allocated port for a service.
        
        Args:
            service: Service name
            
        Returns:
            Port number or None if not allocated
        """
        key = f"{self.environment_id}_{service}"
        if key in self._allocations:
            return self._allocations[key].port
        return None
    
    def get_all_ports(self) -> Dict[str, int]:
        """
        Get all allocated ports for this environment.
        
        Returns:
            Dictionary mapping service names to ports
        """
        ports = {}
        for allocation in self._allocations.values():
            if allocation.environment_id == self.environment_id:
                ports[allocation.service_name] = allocation.port
        return ports


# Convenience functions
def allocate_test_ports(services: List[str], 
                       test_id: Optional[str] = None,
                       port_range: PortRange = PortRange.SHARED_TEST) -> PortAllocationResult:
    """
    Convenience function to allocate ports for a test.
    
    Args:
        services: List of service names
        test_id: Optional test identifier
        port_range: Port range to use
        
    Returns:
        PortAllocationResult
    """
    allocator = DynamicPortAllocator(port_range=port_range, test_id=test_id)
    
    # Clean up old allocations first
    allocator.cleanup_expired_allocations()
    
    # Allocate ports
    return allocator.allocate_ports(services)


def release_test_ports(environment_id: str, services: Optional[List[str]] = None) -> None:
    """
    Convenience function to release test ports.
    
    Args:
        environment_id: Environment identifier
        services: Services to release, None for all
    """
    allocator = DynamicPortAllocator(environment_id=environment_id)
    allocator.release_ports(services)