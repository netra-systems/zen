"""Service discovery module for dynamic port allocation in tests."""

import json
import asyncio
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ServiceInfo:
    """Information about a discovered service."""
    name: str
    port: int
    health_url: str
    base_url: str
    pid: Optional[int] = None
    started_at: Optional[str] = None
    
    @property
    def websocket_url(self) -> str:
        """Get WebSocket URL for the service."""
        return f"ws://localhost:{self.port}/ws"


class ServiceDiscovery:
    """Manages service discovery for dynamically allocated ports."""
    
    def __init__(self, discovery_dir: Path = None):
        """Initialize service discovery.
        
        Args:
            discovery_dir: Directory containing service discovery files.
                         Defaults to .service_discovery in current directory.
        """
        self.discovery_dir = discovery_dir or Path(".service_discovery")
        self._service_cache: Dict[str, ServiceInfo] = {}
        
    def ensure_discovery_dir(self) -> None:
        """Ensure the discovery directory exists."""
        self.discovery_dir.mkdir(exist_ok=True)
        
    async def wait_for_service(self, service_name: str, timeout: float = 30.0) -> ServiceInfo:
        """Wait for a service to register its discovery information.
        
        Args:
            service_name: Name of the service to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            ServiceInfo for the discovered service
            
        Raises:
            TimeoutError: If service doesn't register within timeout
        """
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                return await self.get_service_info(service_name)
            except FileNotFoundError:
                await asyncio.sleep(0.5)
                
        raise TimeoutError(f"Service {service_name} did not register within {timeout}s")
    
    async def get_service_info(self, service_name: str, use_cache: bool = True) -> ServiceInfo:
        """Get service information from discovery files.
        
        Args:
            service_name: Name of the service (e.g., 'auth', 'backend')
            use_cache: Whether to use cached service info
            
        Returns:
            ServiceInfo object with service details
            
        Raises:
            FileNotFoundError: If service discovery file doesn't exist
        """
        if use_cache and service_name in self._service_cache:
            return self._service_cache[service_name]
            
        info_file = self.discovery_dir / f"{service_name}.json"
        
        if not info_file.exists():
            raise FileNotFoundError(f"Service discovery file not found: {info_file}")
            
        try:
            data = json.loads(info_file.read_text())
            
            service_info = ServiceInfo(
                name=service_name,
                port=data["port"],
                health_url=data.get("health_url", "/health"),
                base_url=f"http://localhost:{data['port']}",
                pid=data.get("pid"),
                started_at=data.get("started_at")
            )
            
            self._service_cache[service_name] = service_info
            return service_info
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse service discovery file {info_file}: {e}")
            raise
            
    async def register_service(self, service_name: str, port: int, 
                             health_url: str = "/health", 
                             pid: Optional[int] = None,
                             extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Register a service in the discovery system.
        
        Args:
            service_name: Name of the service
            port: Port the service is running on
            health_url: Health check endpoint path
            pid: Process ID of the service
            extra_data: Additional data to store
        """
        self.ensure_discovery_dir()
        
        info_file = self.discovery_dir / f"{service_name}.json"
        
        data = {
            "port": port,
            "health_url": health_url,
            "pid": pid,
            "started_at": asyncio.get_event_loop().time(),
            **(extra_data or {})
        }
        
        info_file.write_text(json.dumps(data, indent=2))
        logger.info(f"Registered service {service_name} on port {port}")
        
        # Clear cache for this service
        self._service_cache.pop(service_name, None)
        
    async def discover_all_services(self) -> Dict[str, ServiceInfo]:
        """Discover all registered services.
        
        Returns:
            Dictionary mapping service names to ServiceInfo objects
        """
        services = {}
        
        if not self.discovery_dir.exists():
            return services
            
        for info_file in self.discovery_dir.glob("*.json"):
            service_name = info_file.stem
            try:
                services[service_name] = await self.get_service_info(service_name)
            except Exception as e:
                logger.warning(f"Failed to discover service {service_name}: {e}")
                
        return services
        
    def cleanup_discovery_files(self) -> None:
        """Remove all discovery files (useful for test cleanup)."""
        if self.discovery_dir.exists():
            for info_file in self.discovery_dir.glob("*.json"):
                try:
                    info_file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to remove discovery file {info_file}: {e}")
                    
        self._service_cache.clear()
        
    async def get_service_url(self, service_name: str, path: str = "") -> str:
        """Get full URL for a service endpoint.
        
        Args:
            service_name: Name of the service
            path: Optional path to append to base URL
            
        Returns:
            Full URL for the service endpoint
        """
        info = await self.get_service_info(service_name)
        return f"{info.base_url}{path}"
        
    async def get_websocket_url(self, service_name: str, token: Optional[str] = None) -> str:
        """Get WebSocket URL for a service.
        
        Args:
            service_name: Name of the service
            token: Optional auth token to include in query params
            
        Returns:
            WebSocket URL with optional token
        """
        info = await self.get_service_info(service_name)
        ws_url = info.websocket_url
        
        if token:
            ws_url = f"{ws_url}?token={token}"
            
        return ws_url