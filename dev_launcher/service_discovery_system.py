"""Service Discovery System for Dynamic Port Management

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Environment Reliability
- Value Impact: Eliminates port conflicts and enables seamless multi-service startup
- Strategic Impact: Ensures consistent development experience across all environments

FIX: Addresses Test 1.3 - Service port conflicts during startup by implementing
proper service discovery with dynamic port allocation and health checking.
"""

import asyncio
import json
import logging
import socket
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class ServiceEndpoint:
    """Service endpoint configuration."""
    service_name: str
    host: str
    port: int
    protocol: str = "http"
    health_endpoint: Optional[str] = "/health"
    status: str = "unknown"  # unknown, starting, healthy, unhealthy
    last_check: Optional[float] = None
    instance_id: str = None
    
    def __post_init__(self):
        if self.instance_id is None:
            self.instance_id = str(uuid4())[:8]
    
    @property
    def base_url(self) -> str:
        """Get base URL for the service."""
        return f"{self.protocol}://{self.host}:{self.port}"
    
    @property
    def health_url(self) -> str:
        """Get health check URL for the service."""
        if self.health_endpoint:
            return f"{self.base_url}{self.health_endpoint}"
        return None


class ServiceDiscoverySystem:
    """Centralized service discovery system with dynamic port management."""
    
    def __init__(self, discovery_file: Optional[Path] = None):
        """Initialize service discovery system.
        
        Args:
            discovery_file: Path to service discovery file (defaults to .dev_services_discovery.json)
        """
        self.discovery_file = discovery_file or Path(".dev_services_discovery.json")
        self.services: Dict[str, ServiceEndpoint] = {}
        self.port_reservations: Dict[int, str] = {}  # port -> service_name
        self.health_check_interval = 10  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        logger.info(f"ServiceDiscoverySystem initialized with discovery file: {self.discovery_file}")
    
    def is_port_available(self, port: int, host: str = "127.0.0.1") -> bool:
        """Check if a port is available for binding.
        
        Args:
            port: Port number to check
            host: Host address to check (default: 127.0.0.1)
            
        Returns:
            True if port is available, False otherwise
        
        Raises:
            ValueError: If port is not in valid range (0-65535)
        """
        # Validate port range (0-65535 is valid TCP/UDP port range)
        if not isinstance(port, int) or port < 0 or port > 65535:
            raise ValueError(f"Port must be an integer between 0 and 65535, got: {port}")
        
        # Port 0 is special (let OS choose), ports 1-1023 require elevated privileges
        if port == 0:
            return True  # Let OS choose
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((host, port))
                return True
        except OSError:
            return False
    
    def find_available_port(
        self, 
        preferred_port: Optional[int] = None, 
        port_range: Tuple[int, int] = (8000, 9000),
        host: str = "127.0.0.1"
    ) -> Optional[int]:
        """Find an available port within the specified range.
        
        Args:
            preferred_port: Preferred port number (checked first)
            port_range: Range of ports to search (min_port, max_port)
            host: Host address to bind to
            
        Returns:
            Available port number or None if none found
        """
        # Try preferred port first
        if preferred_port and self.is_port_available(preferred_port, host):
            return preferred_port
        
        # Search within range
        min_port, max_port = port_range
        for port in range(min_port, max_port + 1):
            if port not in self.port_reservations and self.is_port_available(port, host):
                return port
        
        logger.warning(f"No available ports found in range {port_range}")
        return None
    
    def register_service(
        self,
        service_name: str,
        host: str = "127.0.0.1",
        preferred_port: Optional[int] = None,
        port_range: Tuple[int, int] = (8000, 9000),
        protocol: str = "http",
        health_endpoint: Optional[str] = "/health"
    ) -> Optional[ServiceEndpoint]:
        """Register a service and allocate a port.
        
        Args:
            service_name: Name of the service
            host: Host address
            preferred_port: Preferred port number
            port_range: Port range to search
            protocol: Service protocol (http/https/ws)
            health_endpoint: Health check endpoint path
            
        Returns:
            ServiceEndpoint if successful, None if failed
        """
        logger.info(f"Registering service '{service_name}' with preferred port {preferred_port}")
        
        # Check if service already registered
        if service_name in self.services:
            existing = self.services[service_name]
            if self.is_port_available(existing.port, existing.host):
                logger.info(f"Service '{service_name}' already registered on port {existing.port}")
                return existing
            else:
                logger.warning(f"Service '{service_name}' port {existing.port} no longer available, re-registering")
                self.unregister_service(service_name)
        
        # Find available port
        port = self.find_available_port(preferred_port, port_range, host)
        if port is None:
            logger.error(f"Failed to find available port for service '{service_name}'")
            return None
        
        # Create service endpoint
        endpoint = ServiceEndpoint(
            service_name=service_name,
            host=host,
            port=port,
            protocol=protocol,
            health_endpoint=health_endpoint,
            status="starting"
        )
        
        # Register service and reserve port
        self.services[service_name] = endpoint
        self.port_reservations[port] = service_name
        
        # Save to discovery file
        self._save_discovery_file()
        
        logger.info(f"Service '{service_name}' registered successfully on {endpoint.base_url}")
        return endpoint
    
    def unregister_service(self, service_name: str) -> bool:
        """Unregister a service and free its port.
        
        Args:
            service_name: Name of the service to unregister
            
        Returns:
            True if service was unregistered, False if not found
        """
        if service_name not in self.services:
            logger.warning(f"Service '{service_name}' not found for unregistration")
            return False
        
        endpoint = self.services[service_name]
        
        # Remove port reservation
        if endpoint.port in self.port_reservations:
            del self.port_reservations[endpoint.port]
        
        # Remove service
        del self.services[service_name]
        
        # Update discovery file
        self._save_discovery_file()
        
        logger.info(f"Service '{service_name}' unregistered, port {endpoint.port} freed")
        return True
    
    def get_service(self, service_name: str) -> Optional[ServiceEndpoint]:
        """Get service endpoint by name.
        
        Args:
            service_name: Name of the service
            
        Returns:
            ServiceEndpoint if found, None otherwise
        """
        return self.services.get(service_name)
    
    def get_service_url(self, service_name: str) -> Optional[str]:
        """Get service base URL by name.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service URL if found, None otherwise
        """
        endpoint = self.get_service(service_name)
        return endpoint.base_url if endpoint else None
    
    def get_all_services(self) -> Dict[str, ServiceEndpoint]:
        """Get all registered services."""
        return self.services.copy()
    
    def list_services(self) -> List[Dict[str, str]]:
        """List all services with their status.
        
        Returns:
            List of service information dictionaries
        """
        services = []
        for name, endpoint in self.services.items():
            services.append({
                "name": name,
                "url": endpoint.base_url,
                "status": endpoint.status,
                "instance_id": endpoint.instance_id,
                "last_check": endpoint.last_check
            })
        return services
    
    async def check_service_health(self, service_name: str) -> bool:
        """Check health of a specific service.
        
        Args:
            service_name: Name of the service to check
            
        Returns:
            True if service is healthy, False otherwise
        """
        endpoint = self.get_service(service_name)
        if not endpoint or not endpoint.health_url:
            return False
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(endpoint.health_url)
                is_healthy = response.status_code == 200
                
                endpoint.status = "healthy" if is_healthy else "unhealthy"
                endpoint.last_check = time.time()
                
                return is_healthy
                
        except Exception as e:
            logger.debug(f"Health check failed for '{service_name}': {e}")
            endpoint.status = "unhealthy"
            endpoint.last_check = time.time()
            return False
    
    async def start_health_monitoring(self):
        """Start continuous health monitoring of registered services."""
        if self._health_check_task:
            logger.warning("Health monitoring already started")
            return
        
        logger.info("Starting service health monitoring...")
        self._health_check_task = asyncio.create_task(self._health_check_loop())
    
    async def stop_health_monitoring(self):
        """Stop health monitoring."""
        if self._health_check_task:
            logger.info("Stopping service health monitoring...")
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
    
    async def _health_check_loop(self):
        """Continuous health checking loop."""
        while not self._shutdown:
            try:
                # Check health of all services
                for service_name in list(self.services.keys()):
                    if self._shutdown:
                        break
                    
                    await self.check_service_health(service_name)
                    await asyncio.sleep(0.1)  # Brief pause between checks
                
                # Update discovery file with latest status
                self._save_discovery_file()
                
                # Wait for next check interval
                await asyncio.sleep(self.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    def _save_discovery_file(self):
        """Save service discovery information to file."""
        try:
            discovery_data = {
                "services": {
                    name: asdict(endpoint) 
                    for name, endpoint in self.services.items()
                },
                "port_reservations": self.port_reservations,
                "last_updated": time.time()
            }
            
            with open(self.discovery_file, 'w') as f:
                json.dump(discovery_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save discovery file: {e}")
    
    def load_discovery_file(self) -> bool:
        """Load service discovery information from file.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        if not self.discovery_file.exists():
            logger.info("No existing discovery file found")
            return False
        
        try:
            with open(self.discovery_file, 'r') as f:
                data = json.load(f)
            
            # Load services
            for name, service_data in data.get("services", {}).items():
                endpoint = ServiceEndpoint(**service_data)
                # Only load if port is still available or already reserved by this service
                if (endpoint.port not in self.port_reservations or 
                    self.port_reservations.get(endpoint.port) == name):
                    self.services[name] = endpoint
                    self.port_reservations[endpoint.port] = name
            
            # Load additional port reservations
            for port_str, service_name in data.get("port_reservations", {}).items():
                port = int(port_str)
                if port not in self.port_reservations:
                    self.port_reservations[port] = service_name
            
            logger.info(f"Loaded {len(self.services)} services from discovery file")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load discovery file: {e}")
            return False
    
    async def cleanup(self):
        """Clean up resources and stop monitoring."""
        logger.info("Cleaning up ServiceDiscoverySystem...")
        self._shutdown = True
        
        await self.stop_health_monitoring()
        
        # Clear all services and reservations
        self.services.clear()
        self.port_reservations.clear()
        
        # Remove discovery file
        if self.discovery_file.exists():
            try:
                self.discovery_file.unlink()
                logger.info("Discovery file removed")
            except Exception as e:
                logger.error(f"Failed to remove discovery file: {e}")
        
        logger.info("ServiceDiscoverySystem cleanup complete")


# Global instance for application use
service_discovery = ServiceDiscoverySystem()


# Convenience functions
def register_service(service_name: str, preferred_port: Optional[int] = None, **kwargs) -> Optional[ServiceEndpoint]:
    """Convenience function to register a service."""
    return service_discovery.register_service(service_name, preferred_port=preferred_port, **kwargs)


def get_service_url(service_name: str) -> Optional[str]:
    """Convenience function to get service URL."""
    return service_discovery.get_service_url(service_name)


def unregister_service(service_name: str) -> bool:
    """Convenience function to unregister a service."""
    return service_discovery.unregister_service(service_name)