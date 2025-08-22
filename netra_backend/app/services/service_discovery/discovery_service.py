"""
Service Discovery Service

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide service discovery functionality for tests
- Value Impact: Enables service discovery tests to execute without import errors
- Strategic Impact: Enables service discovery functionality validation
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ServiceDiscoveryService:
    """Service for discovering and managing available services."""
    
    def __init__(self):
        """Initialize service discovery."""
        self.services: Dict[str, Dict[str, Any]] = {}
        self.service_endpoints: Dict[str, List[Any]] = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize the service discovery service."""
        self._initialized = True
        logger.info("Service discovery initialized")
    
    async def shutdown(self):
        """Shutdown the service discovery service."""
        self._initialized = False
        logger.info("Service discovery shutdown")
    
    async def register_service(self, service_name: str, endpoints: List[Any]) -> None:
        """Register a service with its endpoints."""
        self.services[service_name] = {
            "name": service_name,
            "endpoints": endpoints,
            "registered_at": time.time(),
            "healthy": True
        }
        self.service_endpoints[service_name] = endpoints
        logger.info(f"Registered service {service_name} with {len(endpoints)} endpoints")
    
    def register_service_sync(self, service_name: str, service_info: Dict[str, Any]) -> None:
        """Synchronously register a service."""
        self.services[service_name] = service_info
    
    async def deregister_service(self, service_name: str) -> None:
        """Deregister a service."""
        if service_name in self.services:
            del self.services[service_name]
        if service_name in self.service_endpoints:
            del self.service_endpoints[service_name]
        logger.info(f"Deregistered service {service_name}")
    
    def deregister_service_sync(self, service_name: str) -> None:
        """Synchronously deregister a service."""
        if service_name in self.services:
            del self.services[service_name]
    
    def get_service(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get service information."""
        return self.services.get(service_name)
    
    def get_service_endpoints(self, service_name: str) -> Optional[List[Any]]:
        """Get endpoints for a service."""
        return self.service_endpoints.get(service_name)
    
    def get_all_services(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered services."""
        return self.services.copy()
    
    def get_healthy_services(self) -> Dict[str, Dict[str, Any]]:
        """Get all healthy services."""
        return {
            service_name: info 
            for service_name, info in self.services.items() 
            if info.get('healthy', True)
        }
    
    async def health_check(self, service_name: str) -> bool:
        """Check if service is healthy."""
        service = self.get_service(service_name)
        return service is not None and service.get('healthy', True)
    
    async def update_service_health(self, service_name: str, health_status: str) -> bool:
        """Update health status of a service."""
        if service_name in self.services:
            self.services[service_name]["healthy"] = (health_status == "healthy")
            self.services[service_name]["health_status"] = health_status
            self.services[service_name]["last_health_check"] = time.time()
            logger.info(f"Updated health status for service {service_name} to {health_status}")
            return True
        return False
    
    def update_service_health_sync(self, service_name: str, health_status: str) -> bool:
        """Synchronously update health status of a service."""
        if service_name in self.services:
            self.services[service_name]["healthy"] = (health_status == "healthy")
            return True
        return False
    
    def get_service_count(self) -> int:
        """Get total number of registered services."""
        return len(self.services)
    
    def get_healthy_service_count(self) -> int:
        """Get number of healthy services."""
        return len(self.get_healthy_services())
    
    def is_service_healthy(self, service_name: str) -> bool:
        """Check if a specific service is healthy."""
        service = self.get_service(service_name)
        return service is not None and service.get('healthy', True)