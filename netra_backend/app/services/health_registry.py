"""
Global registry for health services across the platform.
"""

from typing import Dict, Optional

from netra_backend.app.services.unified_health_service import UnifiedHealthService


class HealthRegistry:
    """Global registry for health services across the platform."""
    
    def __init__(self):
        self._services: Dict[str, UnifiedHealthService] = {}
        self._default_service: Optional[UnifiedHealthService] = None
    
    def register_service(self, service_name: str, health_service: UnifiedHealthService) -> None:
        """Register a health service."""
        self._services[service_name] = health_service
        if not self._default_service:
            self._default_service = health_service
    
    def get_service(self, service_name: str) -> Optional[UnifiedHealthService]:
        """Get a specific health service."""
        return self._services.get(service_name)
    
    def get_default_service(self) -> Optional[UnifiedHealthService]:
        """Get the default health service."""
        return self._default_service
    
    def get_all_services(self) -> Dict[str, UnifiedHealthService]:
        """Get all registered health services."""
        return self._services.copy()


# Global registry instance
health_registry = HealthRegistry()