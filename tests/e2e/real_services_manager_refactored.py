"""
Real Services Manager for E2E Testing - Refactored to use DevLauncher
Manages starting/stopping real services using the dev_launcher infrastructure.

CRITICAL REQUIREMENTS:
- Use dev_launcher for all service management
- Support dynamic port allocation
- Health check validation for all services
- Proper cleanup on test completion
- NO MOCKING - real services only
- Handle Windows/Unix compatibility
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from dev_launcher.config import LauncherConfig
from dev_launcher.discovery import ServiceDiscovery, ServiceInfo
from dev_launcher.launcher import DevLauncher
from tests.clients import TestClientFactory

logger = logging.getLogger(__name__)


class RealServicesManager:
    """Manages real services for E2E testing using dev_launcher."""
    
    def __init__(self, dynamic_ports: bool = True, test_mode: bool = True):
        """Initialize the real services manager.
        
        Args:
            dynamic_ports: Use dynamic port allocation
            test_mode: Run in test mode with test configurations
        """
        self.dynamic_ports = dynamic_ports
        self.test_mode = test_mode
        self.launcher: Optional[DevLauncher] = None
        self.discovery: Optional[ServiceDiscovery] = None
        self.client_factory: Optional[TestClientFactory] = None
        self._service_info: Dict[str, ServiceInfo] = {}
        
    async def start_all_services(self, skip_frontend: bool = True) -> None:
        """Start all services using dev_launcher.
        
        Args:
            skip_frontend: Skip starting frontend service (default True for tests)
        """
        # Configure services to start
        services = ["auth", "backend"]
        if not skip_frontend:
            services.append("frontend")
            
        # Create launcher configuration
        config = LauncherConfig(
            dynamic_ports=self.dynamic_ports,
            test_mode=self.test_mode,
            startup_timeout=30,
            services=services
        )
        
        # Initialize launcher
        self.launcher = DevLauncher(config)
        
        # Start all services
        logger.info(f"Starting services: {services}")
        success = await self.launcher.run()
        
        if not success:
            raise RuntimeError("Failed to start services via dev_launcher")
            
        # Initialize service discovery
        self.discovery = ServiceDiscovery()
        
        # Wait for all services to register
        for service in services:
            info = await self.discovery.wait_for_service(service, timeout=30.0)
            self._service_info[service] = info
            logger.info(f"{service} service ready on port {info.port}")
            
        # Initialize client factory
        self.client_factory = TestClientFactory(self.discovery)
        
        logger.info("All services started and healthy")
        
    async def stop_all_services(self) -> None:
        """Stop all services and cleanup resources."""
        if self.client_factory:
            await self.client_factory.cleanup()
            
        if self.launcher:
            await self.launcher.shutdown()
            logger.info("All services stopped via dev_launcher")
            
        # Clean discovery files
        if self.discovery:
            self.discovery.cleanup_discovery_files()
            
    def get_service_urls(self) -> Dict[str, str]:
        """Get URLs for all running services.
        
        Returns:
            Dictionary mapping service names to their base URLs
        """
        return {
            name: info.base_url
            for name, info in self._service_info.items()
        }
        
    def get_service_ports(self) -> Dict[str, int]:
        """Get ports for all running services.
        
        Returns:
            Dictionary mapping service names to their ports
        """
        return {
            name: info.port
            for name, info in self._service_info.items()
        }
        
    async def health_status(self) -> Dict[str, Any]:
        """Get health status of all services.
        
        Returns:
            Dictionary with health status for each service
        """
        if not self.launcher:
            return {}
            
        status = {}
        
        for name, info in self._service_info.items():
            # Check if service is healthy via HTTP
            try:
                if self.client_factory:
                    if name == "auth":
                        client = await self.client_factory.create_auth_client()
                        is_healthy = await client.health_check()
                    elif name == "backend":
                        client = await self.client_factory.create_backend_client()
                        is_healthy = await client.health_check()
                    else:
                        is_healthy = False
                else:
                    is_healthy = False
                    
            except Exception:
                is_healthy = False
                
            status[name] = {
                "ready": is_healthy,
                "port": info.port,
                "url": info.base_url,
                "pid": info.pid
            }
            
        return status
        
    def is_all_ready(self) -> bool:
        """Check if all services are ready.
        
        Returns:
            True if all services have been started and discovered
        """
        return len(self._service_info) > 0 and all(
            info.port > 0 for info in self._service_info.values()
        )
        
    async def get_auth_client(self):
        """Get authenticated auth service client.
        
        Returns:
            AuthTestClient instance
        """
        if not self.client_factory:
            raise RuntimeError("Services not started")
        return await self.client_factory.create_auth_client()
        
    async def get_backend_client(self, token: Optional[str] = None):
        """Get backend service client.
        
        Args:
            token: Optional JWT token for authentication
            
        Returns:
            BackendTestClient instance
        """
        if not self.client_factory:
            raise RuntimeError("Services not started")
        return await self.client_factory.create_backend_client(token)
        
    async def get_websocket_client(self, token: str):
        """Get WebSocket client.
        
        Args:
            token: JWT token for authentication
            
        Returns:
            WebSocketTestClient instance
        """
        if not self.client_factory:
            raise RuntimeError("Services not started")
        return await self.client_factory.create_websocket_client(token)
        
    async def create_test_user(self, email: Optional[str] = None):
        """Create a test user and get authentication token.
        
        Args:
            email: Optional email address for the test user
            
        Returns:
            Dictionary with user info and token
        """
        auth_client = await self.get_auth_client()
        return await auth_client.create_test_user(email)
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_all_services()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_all_services()


# Factory function for backward compatibility
async def create_real_services_manager(
    dynamic_ports: bool = True,
    test_mode: bool = True,
    skip_frontend: bool = True
) -> RealServicesManager:
    """Create and start a real services manager.
    
    Args:
        dynamic_ports: Use dynamic port allocation
        test_mode: Run in test mode
        skip_frontend: Skip starting frontend service
        
    Returns:
        Started RealServicesManager instance
    """
    manager = RealServicesManager(dynamic_ports=dynamic_ports, test_mode=test_mode)
    await manager.start_all_services(skip_frontend=skip_frontend)
    return manager