"""
Port Allocation Coordinator with Reservation System.

This module provides atomic port allocation with conflict resolution
to prevent port binding race conditions during service startup.

Business Value: Platform/Internal - Development Velocity - Prevents port conflicts
that cause service startup failures in development environments.
"""

import asyncio
import logging
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class PortState(Enum):
    """States of a port in the allocation system."""
    AVAILABLE = "available"
    RESERVED = "reserved"
    ALLOCATED = "allocated" 
    IN_USE = "in_use"
    BLOCKED = "blocked"


@dataclass
class PortReservation:
    """Port reservation information."""
    port: int
    service_name: str
    reserved_at: float
    allocated_at: Optional[float] = None
    expires_at: Optional[float] = None
    state: PortState = PortState.RESERVED
    process_id: Optional[int] = None
    
    def is_expired(self) -> bool:
        """Check if reservation has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
    
    def get_age(self) -> float:
        """Get age of reservation in seconds."""
        return time.time() - self.reserved_at


@dataclass 
class AllocationResult:
    """Result of a port allocation attempt."""
    success: bool
    port: Optional[int] = None
    service_name: Optional[str] = None
    error_message: Optional[str] = None
    conflicting_service: Optional[str] = None
    alternative_ports: List[int] = field(default_factory=list)


class PortAllocator:
    """
    Centralized port allocation coordinator with atomic reservations.
    
    Prevents port binding race conditions by implementing a reservation
    system with conflict detection and resolution.
    """
    
    def __init__(self, 
                 default_reservation_timeout: float = 60.0,
                 cleanup_interval: float = 30.0):
        """
        Initialize port allocator.
        
        Args:
            default_reservation_timeout: Default reservation timeout in seconds
            cleanup_interval: Interval between cleanup runs in seconds
        """
        self.reservations: Dict[int, PortReservation] = {}
        self.service_ports: Dict[str, Set[int]] = {}  # service -> set of ports
        self.port_ranges: Dict[str, Tuple[int, int]] = {
            'system': (1, 1023),
            'ephemeral': (32768, 65535),
            'development': (8000, 9999),
            'auth_services': (8080, 8090), 
            'backend_services': (8000, 8010),
            'frontend_services': (3000, 3010)
        }
        self.blocked_ports: Set[int] = set()
        self.default_reservation_timeout = default_reservation_timeout
        self.cleanup_interval = cleanup_interval
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(f"PortAllocator initialized (reservation_timeout: {default_reservation_timeout}s)")
    
    async def start(self) -> None:
        """Start the port allocator background tasks."""
        if self._running:
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("PortAllocator started")
    
    async def stop(self) -> None:
        """Stop the port allocator background tasks."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("PortAllocator stopped")
    
    async def reserve_port(self, service_name: str, 
                          preferred_port: Optional[int] = None,
                          port_range: Optional[Tuple[int, int]] = None,
                          timeout: Optional[float] = None) -> AllocationResult:
        """
        Reserve a port for a service with atomic allocation.
        
        Args:
            service_name: Name of the service requesting the port
            preferred_port: Preferred port number
            port_range: Range to search for available ports (min, max)
            timeout: Reservation timeout (None for default)
            
        Returns:
            AllocationResult with reservation details
        """
        async with self._lock:
            return await self._reserve_port_impl(service_name, preferred_port, port_range, timeout)
    
    async def _reserve_port_impl(self, service_name: str, 
                                preferred_port: Optional[int] = None,
                                port_range: Optional[Tuple[int, int]] = None,
                                timeout: Optional[float] = None) -> AllocationResult:
        """Internal implementation of port reservation."""
        timeout = timeout or self.default_reservation_timeout
        current_time = time.time()
        expires_at = current_time + timeout
        
        logger.info(f"Reserving port for service {service_name}")
        
        # Clean up expired reservations first
        await self._cleanup_expired_reservations()
        
        # Determine port search range
        search_range = port_range or self._get_default_range(service_name)
        
        # Try preferred port first
        if preferred_port:
            if await self._can_reserve_port(preferred_port, service_name):
                reservation = PortReservation(
                    port=preferred_port,
                    service_name=service_name,
                    reserved_at=current_time,
                    expires_at=expires_at,
                    state=PortState.RESERVED
                )
                
                self.reservations[preferred_port] = reservation
                self._track_service_port(service_name, preferred_port)
                
                logger.info(f"Reserved preferred port {preferred_port} for {service_name}")
                return AllocationResult(
                    success=True,
                    port=preferred_port,
                    service_name=service_name
                )
            else:
                # Get conflict information
                conflicting_service = None
                if preferred_port in self.reservations:
                    conflicting_service = self.reservations[preferred_port].service_name
                
                logger.warning(f"Preferred port {preferred_port} not available for {service_name}, "
                             f"conflicting with: {conflicting_service}")
        
        # Search for available port in range
        alternative_ports = []
        start_port, end_port = search_range
        
        for port in range(start_port, end_port + 1):
            if await self._can_reserve_port(port, service_name):
                reservation = PortReservation(
                    port=port,
                    service_name=service_name,
                    reserved_at=current_time,
                    expires_at=expires_at,
                    state=PortState.RESERVED
                )
                
                self.reservations[port] = reservation
                self._track_service_port(service_name, port)
                
                logger.info(f"Reserved port {port} for {service_name} (searched {port - start_port + 1} ports)")
                return AllocationResult(
                    success=True,
                    port=port,
                    service_name=service_name,
                    alternative_ports=alternative_ports
                )
            else:
                alternative_ports.append(port)
                # Limit alternative port tracking
                if len(alternative_ports) > 10:
                    alternative_ports.pop(0)
        
        # No ports available
        logger.error(f"No ports available for {service_name} in range {search_range}")
        return AllocationResult(
            success=False,
            service_name=service_name,
            error_message=f"No available ports in range {search_range}",
            alternative_ports=alternative_ports[:5]  # Return first 5 as alternatives
        )
    
    async def _can_reserve_port(self, port: int, service_name: str) -> bool:
        """
        Check if a port can be reserved by the service.
        
        Args:
            port: Port number to check
            service_name: Name of the requesting service
            
        Returns:
            True if port can be reserved
        """
        # Check if port is blocked
        if port in self.blocked_ports:
            return False
        
        # Check if port is in system range (generally avoid)
        if self.port_ranges['system'][0] <= port <= self.port_ranges['system'][1]:
            return False
        
        # Check existing reservations
        if port in self.reservations:
            reservation = self.reservations[port]
            
            # Allow same service to re-reserve
            if reservation.service_name == service_name:
                return True
            
            # Check if reservation is expired
            if reservation.is_expired():
                # Will be cleaned up, so available
                return True
            
            # Active reservation by another service
            return False
        
        # Check if port is actually available on the system
        return await self._is_port_system_available(port)
    
    async def _is_port_system_available(self, port: int) -> bool:
        """Check if port is available at the system level."""
        # Basic socket binding test
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('127.0.0.1', port))
                return True
        except OSError:
            pass
        
        # Platform-specific check
        if sys.platform == "win32":
            return await self._windows_port_available(port)
        else:
            return await self._unix_port_available(port)
    
    async def _windows_port_available(self, port: int) -> bool:
        """Windows-specific port availability check."""
        try:
            result = await asyncio.create_subprocess_exec(
                "netstat", "-ano",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            
            if result.returncode == 0:
                output = stdout.decode()
                for line in output.splitlines():
                    if f":{port} " in line and "LISTENING" in line:
                        return False
            return True
        except Exception:
            # Assume available if check fails
            return True
    
    async def _unix_port_available(self, port: int) -> bool:
        """Unix-specific port availability check."""
        try:
            result = await asyncio.create_subprocess_exec(
                "lsof", "-i", f":{port}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            
            # lsof returns 0 if port is in use
            return result.returncode != 0
        except FileNotFoundError:
            # lsof not available, fall back to socket test only
            return True
        except Exception:
            return True
    
    def _get_default_range(self, service_name: str) -> Tuple[int, int]:
        """Get default port range for a service type."""
        service_lower = service_name.lower()
        
        if 'auth' in service_lower:
            return self.port_ranges['auth_services']
        elif 'backend' in service_lower or 'api' in service_lower:
            return self.port_ranges['backend_services']
        elif 'frontend' in service_lower or 'web' in service_lower:
            return self.port_ranges['frontend_services']
        else:
            return self.port_ranges['development']
    
    def _track_service_port(self, service_name: str, port: int) -> None:
        """Track port allocation for a service."""
        if service_name not in self.service_ports:
            self.service_ports[service_name] = set()
        self.service_ports[service_name].add(port)
    
    async def confirm_allocation(self, port: int, service_name: str, 
                               process_id: Optional[int] = None) -> bool:
        """
        Confirm that a service has successfully bound to its reserved port.
        
        Args:
            port: Port that was allocated
            service_name: Name of the service
            process_id: Process ID of the service (optional)
            
        Returns:
            True if allocation was confirmed
        """
        async with self._lock:
            if port not in self.reservations:
                logger.error(f"No reservation found for port {port}")
                return False
            
            reservation = self.reservations[port]
            
            if reservation.service_name != service_name:
                logger.error(f"Port {port} reserved by {reservation.service_name}, not {service_name}")
                return False
            
            # Update reservation to allocated state
            reservation.state = PortState.ALLOCATED
            reservation.allocated_at = time.time()
            reservation.expires_at = None  # No longer expires
            reservation.process_id = process_id
            
            logger.info(f"Confirmed allocation of port {port} to {service_name}")
            if process_id:
                logger.debug(f"   ->  Process ID: {process_id}")
            
            return True
    
    async def release_port(self, port: int, service_name: str) -> bool:
        """
        Release a port allocation.
        
        Args:
            port: Port to release
            service_name: Name of the service releasing the port
            
        Returns:
            True if port was released
        """
        async with self._lock:
            if port not in self.reservations:
                logger.warning(f"No reservation found for port {port}")
                return False
            
            reservation = self.reservations[port]
            
            if reservation.service_name != service_name:
                logger.error(f"Cannot release port {port}: owned by {reservation.service_name}, not {service_name}")
                return False
            
            # Remove reservation
            del self.reservations[port]
            
            # Remove from service tracking
            if service_name in self.service_ports:
                self.service_ports[service_name].discard(port)
                if not self.service_ports[service_name]:
                    del self.service_ports[service_name]
            
            logger.info(f"Released port {port} from {service_name}")
            return True
    
    async def release_service_ports(self, service_name: str) -> List[int]:
        """
        Release all ports allocated to a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            List of ports that were released
        """
        async with self._lock:
            if service_name not in self.service_ports:
                return []
            
            ports_to_release = list(self.service_ports[service_name])
            released_ports = []
            
            for port in ports_to_release:
                if port in self.reservations:
                    reservation = self.reservations[port]
                    if reservation.service_name == service_name:
                        del self.reservations[port]
                        released_ports.append(port)
            
            # Clear service tracking
            del self.service_ports[service_name]
            
            if released_ports:
                logger.info(f"Released {len(released_ports)} ports from {service_name}: {released_ports}")
            
            return released_ports
    
    def get_service_ports(self, service_name: str) -> Set[int]:
        """Get all ports allocated to a service."""
        return self.service_ports.get(service_name, set()).copy()
    
    def get_port_status(self, port: int) -> Optional[PortReservation]:
        """Get status of a specific port."""
        return self.reservations.get(port)
    
    def get_allocation_summary(self) -> Dict[str, any]:
        """Get summary of all port allocations."""
        current_time = time.time()
        
        summary = {
            "total_reservations": len(self.reservations),
            "reserved_ports": [],
            "allocated_ports": [],
            "expired_reservations": [],
            "services": {},
            "blocked_ports": list(self.blocked_ports)
        }
        
        for port, reservation in self.reservations.items():
            port_info = {
                "port": port,
                "service": reservation.service_name,
                "state": reservation.state.value,
                "age": reservation.get_age(),
                "process_id": reservation.process_id
            }
            
            if reservation.is_expired():
                summary["expired_reservations"].append(port_info)
            elif reservation.state == PortState.ALLOCATED:
                summary["allocated_ports"].append(port_info)
            else:
                summary["reserved_ports"].append(port_info)
        
        # Service summary
        for service_name, ports in self.service_ports.items():
            summary["services"][service_name] = {
                "port_count": len(ports),
                "ports": sorted(list(ports))
            }
        
        return summary
    
    async def _cleanup_expired_reservations(self) -> None:
        """Clean up expired reservations."""
        current_time = time.time()
        expired_ports = []
        
        for port, reservation in self.reservations.items():
            if reservation.is_expired():
                expired_ports.append(port)
        
        for port in expired_ports:
            reservation = self.reservations[port]
            service_name = reservation.service_name
            
            # Remove reservation
            del self.reservations[port]
            
            # Remove from service tracking
            if service_name in self.service_ports:
                self.service_ports[service_name].discard(port)
                if not self.service_ports[service_name]:
                    del self.service_ports[service_name]
            
            logger.info(f"Cleaned up expired reservation: port {port} from {service_name}")
    
    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired reservations."""
        while self._running:
            try:
                async with self._lock:
                    await self._cleanup_expired_reservations()
                
                await asyncio.sleep(self.cleanup_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(self.cleanup_interval)
    
    def block_port(self, port: int, reason: str = "Manual block") -> None:
        """Block a port from being allocated."""
        self.blocked_ports.add(port)
        logger.info(f"Blocked port {port}: {reason}")
    
    def unblock_port(self, port: int) -> None:
        """Unblock a port."""
        self.blocked_ports.discard(port)
        logger.info(f"Unblocked port {port}")
    
    async def validate_allocations(self) -> Dict[str, List[str]]:
        """
        Validate that all allocated ports are actually in use.
        
        Returns:
            Dictionary with validation issues
        """
        issues = {
            "orphaned_reservations": [],  # Reservations without actual port usage
            "conflicting_allocations": [], # Multiple services claiming same port
            "expired_but_active": []       # Expired reservations but port still in use
        }
        
        for port, reservation in self.reservations.items():
            # Check if port is actually in use
            try:
                in_use = not await self._is_port_system_available(port)
                
                if reservation.state == PortState.ALLOCATED and not in_use:
                    issues["orphaned_reservations"].append(
                        f"Port {port} allocated to {reservation.service_name} but not in use"
                    )
                elif reservation.is_expired() and in_use:
                    issues["expired_but_active"].append(
                        f"Port {port} reservation expired for {reservation.service_name} but still in use"
                    )
                    
            except Exception as e:
                logger.warning(f"Could not validate port {port}: {e}")
        
        return issues


# Global port allocator instance
_global_allocator: Optional[PortAllocator] = None


async def get_global_port_allocator() -> PortAllocator:
    """Get or create the global port allocator instance."""
    global _global_allocator
    
    if _global_allocator is None:
        _global_allocator = PortAllocator()
        await _global_allocator.start()
    
    return _global_allocator


async def cleanup_global_port_allocator() -> None:
    """Clean up the global port allocator instance."""
    global _global_allocator
    
    if _global_allocator:
        await _global_allocator.stop()
        _global_allocator = None