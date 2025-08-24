"""
Port Management for Development Services

This module provides robust port allocation and verification with platform-specific
optimizations for Windows and Unix-like systems.

Windows Features:
- Port availability checking using netstat
- Process identification for port conflicts
- Enhanced port cleanup verification
- Support for dynamic port allocation ranges

Unix Features:
- lsof-based port checking
- Process group awareness
- Signal-based cleanup verification

Business Value: Platform/Internal - Development Velocity - Ensures reliable port
management across different operating systems, reducing development environment conflicts.
"""

import logging
import socket
import subprocess
import sys
import time
from typing import Dict, List, Optional, Set, Tuple

from netra_backend.app.core.network_constants import ServicePorts

logger = logging.getLogger(__name__)


class PortManager:
    """
    Manages port allocation and verification for development services.
    
    Provides platform-specific port management with automatic conflict resolution
    and cleanup verification. Supports both static and dynamic port allocation.
    """
    
    def __init__(self):
        """Initialize port manager with platform detection."""
        self.is_windows = sys.platform == "win32"
        self.allocated_ports: Dict[str, int] = {}
        self.port_processes: Dict[int, str] = {}  # port -> process name mapping
        self.reserved_ranges = {
            'auth_service': (ServicePorts.AUTH_SERVICE_DEFAULT, ServicePorts.AUTH_SERVICE_DEFAULT + 10),
            'backend': (ServicePorts.BACKEND_DEFAULT, ServicePorts.BACKEND_DEFAULT + 5),
            'dynamic': (ServicePorts.DYNAMIC_PORT_MIN, ServicePorts.DYNAMIC_PORT_MAX)
        }
        
        logger.info(f"PortManager initialized for {sys.platform}")
        if self.is_windows:
            logger.info("Windows netstat-based port verification enabled")
        else:
            logger.info("Unix lsof-based port verification enabled")
    
    def allocate_port(self, service_name: str, preferred_port: Optional[int] = None, 
                     port_range: Optional[Tuple[int, int]] = None, max_retries: int = 3) -> Optional[int]:
        """
        Allocate an available port for a service with retry logic for race conditions.
        
        Args:
            service_name: Name of the service requesting the port
            preferred_port: Preferred port number (will be tested first)
            port_range: Range of ports to search (min, max)
            max_retries: Maximum retries for race condition handling
            
        Returns:
            Allocated port number or None if no ports available
        """
        logger.info(f"Allocating port for service: {service_name}")
        
        # Check if service already has an allocated port
        if service_name in self.allocated_ports:
            existing_port = self.allocated_ports[service_name]
            if self._is_port_available(existing_port):
                logger.info(f"Service {service_name} already has port {existing_port}")
                return existing_port
            else:
                logger.warning(f"Previously allocated port {existing_port} no longer available, reallocating")
                self.release_port(service_name)
        
        for retry in range(max_retries + 1):
            if retry > 0:
                logger.debug(f"Port allocation retry {retry} for {service_name}")
                time.sleep(0.1 * retry)  # Exponential backoff
            
            port = self._attempt_port_allocation(service_name, preferred_port, port_range)
            if port is not None:
                # Double-check with race condition protection
                if self._verify_port_allocation(port, service_name):
                    return port
                else:
                    logger.warning(f"Port {port} allocation race condition detected, retrying...")
                    continue
        
        logger.error(f"Failed to allocate port for {service_name} after {max_retries} retries")
        return None
    
    def _attempt_port_allocation(self, service_name: str, preferred_port: Optional[int], 
                                port_range: Optional[Tuple[int, int]]) -> Optional[int]:
        """Attempt to allocate a port without retry logic."""
        # Determine search range
        if port_range:
            start_port, end_port = port_range
        elif service_name.lower() in self.reserved_ranges:
            start_port, end_port = self.reserved_ranges[service_name.lower()]
        else:
            start_port, end_port = self.reserved_ranges['dynamic']
        
        # Try preferred port first if specified
        if preferred_port and self._is_port_allocatable(preferred_port):
            self.allocated_ports[service_name] = preferred_port
            self.port_processes[preferred_port] = service_name
            logger.info(f"Allocated preferred port {preferred_port} to {service_name}")
            return preferred_port
        
        # Search for available port in range
        for port in range(start_port, end_port + 1):
            if self._is_port_allocatable(port):
                self.allocated_ports[service_name] = port
                self.port_processes[port] = service_name
                logger.info(f"Allocated port {port} to {service_name}")
                return port
        
        return None
    
    def _is_port_allocatable(self, port: int) -> bool:
        """
        Check if a port is allocatable (available and not already allocated to another service).
        
        Args:
            port: Port number to check
            
        Returns:
            True if port can be allocated, False otherwise
        """
        # First check if port is already allocated to another service
        if port in self.port_processes:
            logger.debug(f"Port {port} already allocated to {self.port_processes[port]}")
            return False
        
        # Then check if port is available on the system
        return self._is_port_available_with_retry(port)
    
    def _is_port_available_with_retry(self, port: int, retries: int = 2) -> bool:
        """Check port availability with retry for race conditions."""
        for attempt in range(retries + 1):
            if attempt > 0:
                time.sleep(0.05)  # Short delay between retries
            
            if self._is_port_available(port):
                return True
        return False
    
    def _verify_port_allocation(self, port: int, service_name: str) -> bool:
        """Verify that port allocation was successful and handle race conditions."""
        # Wait a brief moment to allow any race conditions to manifest
        time.sleep(0.1)
        
        # Re-check port availability
        if not self._is_port_available(port):
            # Port is no longer available, check if it's our process
            process_info = self.find_process_using_port(port)
            if process_info and service_name.lower() in process_info.lower():
                logger.debug(f"Port {port} correctly allocated to {service_name}")
                return True
            else:
                logger.warning(f"Port {port} taken by another process: {process_info}")
                # Clean up our allocation record
                if service_name in self.allocated_ports and self.allocated_ports[service_name] == port:
                    del self.allocated_ports[service_name]
                if port in self.port_processes:
                    del self.port_processes[port]
                return False
        
        # Port is still available, which means we haven't started the service yet
        return True
    
    def _is_port_available(self, port: int) -> bool:
        """
        Check if a port is available for binding.
        
        Uses platform-specific methods for comprehensive port checking.
        """
        # First, try socket binding test (fast check)
        if not self._socket_bind_test(port):
            return False
        
        # Second, use platform-specific verification
        if self.is_windows:
            return self._windows_port_check(port)
        else:
            return self._unix_port_check(port)
    
    def _socket_bind_test(self, port: int) -> bool:
        """Basic socket binding test."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('127.0.0.1', port))
                return True
        except OSError:
            return False
    
    def _windows_port_check(self, port: int) -> bool:
        """Windows-specific port availability check using netstat."""
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    # Look for exact port match in LISTENING state
                    if f":{port} " in line and "LISTENING" in line:
                        # Extract process info for logging
                        parts = line.split()
                        if parts:
                            pid = parts[-1] if parts else "unknown"
                            logger.debug(f"Port {port} in use by PID {pid}: {line.strip()}")
                        return False
                return True
            else:
                logger.debug(f"netstat failed: {result.stderr}")
                return True  # Assume available if netstat fails
                
        except Exception as e:
            logger.debug(f"Windows port check failed for {port}: {e}")
            return True  # Assume available on error
    
    def _unix_port_check(self, port: int) -> bool:
        """Unix-specific port availability check using lsof."""
        try:
            result = subprocess.run(
                ["lsof", "-i", f":{port}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # lsof returns 0 if port is in use, non-zero if not
            if result.returncode == 0 and result.stdout.strip():
                logger.debug(f"Port {port} in use: {result.stdout.strip()}")
                return False
            return True
            
        except FileNotFoundError:
            # lsof not available, fall back to socket test only
            logger.debug("lsof not available, using socket test only")
            return True
        except Exception as e:
            logger.debug(f"Unix port check failed for {port}: {e}")
            return True  # Assume available on error
    
    def release_port(self, service_name: str) -> bool:
        """
        Release a port allocated to a service.
        
        Args:
            service_name: Name of the service to release port for
            
        Returns:
            True if port was released successfully
        """
        if service_name in self.allocated_ports:
            port = self.allocated_ports[service_name]
            del self.allocated_ports[service_name]
            if port in self.port_processes:
                del self.port_processes[port]
            logger.info(f"Released port {port} from {service_name}")
            return True
        
        logger.warning(f"No port allocated to service {service_name}")
        return False
    
    def get_allocated_port(self, service_name: str) -> Optional[int]:
        """Get the port allocated to a service."""
        return self.allocated_ports.get(service_name)
    
    def get_all_allocated_ports(self) -> Dict[str, int]:
        """Get all currently allocated ports."""
        return self.allocated_ports.copy()
    
    def verify_port_cleanup(self, ports: Set[int], max_attempts: int = 3, 
                           wait_time: float = 1.0) -> Set[int]:
        """
        Verify that specified ports have been released after process termination.
        
        Args:
            ports: Set of ports to verify
            max_attempts: Maximum verification attempts
            wait_time: Time to wait between attempts
            
        Returns:
            Set of ports still in use after verification
        """
        if not ports:
            return set()
        
        logger.info(f"Verifying cleanup of ports: {sorted(ports)}")
        
        for attempt in range(max_attempts):
            if attempt > 0:
                time.sleep(wait_time)
            
            still_in_use = self._get_ports_in_use(ports)
            if not still_in_use:
                logger.info("All ports successfully released")
                return set()
            
            logger.warning(f"Attempt {attempt + 1}: Ports still in use: {sorted(still_in_use)}")
        
        logger.error(f"Ports still in use after {max_attempts} attempts: {sorted(still_in_use)}")
        return still_in_use
    
    def _get_ports_in_use(self, ports: Set[int]) -> Set[int]:
        """Get which ports from the set are still in use."""
        in_use = set()
        
        if self.is_windows:
            in_use = self._windows_get_ports_in_use(ports)
        else:
            in_use = self._unix_get_ports_in_use(ports)
        
        return in_use
    
    def _windows_get_ports_in_use(self, ports: Set[int]) -> Set[int]:
        """Windows-specific method to check which ports are in use."""
        in_use = set()
        
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    for port in ports:
                        if f":{port} " in line and "LISTENING" in line:
                            in_use.add(port)
                            # Log process info if available
                            parts = line.split()
                            if parts:
                                pid = parts[-1]
                                logger.debug(f"Port {port} still in use by PID {pid}")
            
        except Exception as e:
            logger.debug(f"Error checking Windows port usage: {e}")
        
        return in_use
    
    def _unix_get_ports_in_use(self, ports: Set[int]) -> Set[int]:
        """Unix-specific method to check which ports are in use."""
        in_use = set()
        
        for port in ports:
            try:
                result = subprocess.run(
                    ["lsof", "-i", f":{port}"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    in_use.add(port)
                    logger.debug(f"Port {port} still in use: {result.stdout.strip()}")
                    
            except Exception as e:
                logger.debug(f"Error checking Unix port {port}: {e}")
        
        return in_use
    
    def find_process_using_port(self, port: int) -> Optional[str]:
        """
        Find which process is using a specific port.
        
        Args:
            port: Port number to check
            
        Returns:
            Process identifier string or None if not found
        """
        if self.is_windows:
            return self._windows_find_process(port)
        else:
            return self._unix_find_process(port)
    
    def _windows_find_process(self, port: int) -> Optional[str]:
        """Find process using port on Windows."""
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if f":{port} " in line and "LISTENING" in line:
                        parts = line.split()
                        if parts:
                            pid = parts[-1]
                            # Try to get process name
                            try:
                                name_result = subprocess.run(
                                    ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV"],
                                    capture_output=True,
                                    text=True,
                                    timeout=5
                                )
                                if name_result.returncode == 0:
                                    lines = name_result.stdout.strip().split('\n')
                                    if len(lines) > 1:  # Skip header
                                        process_name = lines[1].split(',')[0].strip('"')
                                        return f"{process_name} (PID: {pid})"
                            except Exception:
                                pass
                            return f"PID: {pid}"
                            
        except Exception as e:
            logger.debug(f"Error finding Windows process for port {port}: {e}")
        
        return None
    
    def _unix_find_process(self, port: int) -> Optional[str]:
        """Find process using port on Unix systems."""
        try:
            result = subprocess.run(
                ["lsof", "-i", f":{port}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:  # Skip header
                    parts = lines[1].split()
                    if len(parts) >= 2:
                        return f"{parts[0]} (PID: {parts[1]})"
                        
        except Exception as e:
            logger.debug(f"Error finding Unix process for port {port}: {e}")
        
        return None
    
    def get_port_conflicts(self) -> Dict[int, str]:
        """
        Get information about any port conflicts in allocated ports.
        
        Returns:
            Dictionary mapping port numbers to conflict descriptions
        """
        conflicts = {}
        
        for service_name, port in self.allocated_ports.items():
            if not self._is_port_available(port):
                process_info = self.find_process_using_port(port)
                if process_info:
                    conflicts[port] = f"Port {port} (allocated to {service_name}) in use by {process_info}"
                else:
                    conflicts[port] = f"Port {port} (allocated to {service_name}) is unavailable"
        
        return conflicts
    
    def cleanup_all(self):
        """Clean up all allocated port tracking."""
        released_ports = list(self.allocated_ports.keys())
        self.allocated_ports.clear()
        self.port_processes.clear()
        
        if released_ports:
            logger.info(f"Released port tracking for services: {released_ports}")
    
    def get_recommended_ports(self) -> Dict[str, int]:
        """Get recommended ports for common services."""
        return {
            'backend': ServicePorts.BACKEND_DEFAULT,
            'frontend': ServicePorts.FRONTEND_DEFAULT,
            'auth_service': ServicePorts.AUTH_SERVICE_DEFAULT,
            'postgres': ServicePorts.POSTGRES_DEFAULT,
            'redis': ServicePorts.REDIS_DEFAULT,
            'clickhouse_http': ServicePorts.CLICKHOUSE_HTTP,
            'clickhouse_native': ServicePorts.CLICKHOUSE_NATIVE
        }
    
    def __str__(self) -> str:
        """String representation of current port allocations."""
        if not self.allocated_ports:
            return "PortManager: No ports allocated"
        
        allocations = []
        for service, port in sorted(self.allocated_ports.items()):
            allocations.append(f"{service}: {port}")
        
        return f"PortManager: {', '.join(allocations)}"