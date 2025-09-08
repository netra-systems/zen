"""
Degradation Manager - Core graceful degradation functionality.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Enable graceful degradation during service outages
- Value Impact: Maintains partial functionality when services are down
- Strategic Impact: Prevents complete system failure during partial outages
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DegradationLevel(Enum):
    """System degradation levels."""
    NORMAL = "normal"
    PARTIAL = "partial"
    DEGRADED = "degraded"
    MINIMAL = "minimal"


@dataclass
class DegradationStatus:
    """Current degradation status."""
    level: DegradationLevel = DegradationLevel.NORMAL
    affected_services: List[str] = None
    degraded_features: List[str] = None
    message: str = ""
    
    def __post_init__(self):
        if self.affected_services is None:
            self.affected_services = []
        if self.degraded_features is None:
            self.degraded_features = []


class GracefulDegradationManager:
    """Manager for graceful degradation functionality."""
    
    def __init__(self):
        """Initialize graceful degradation manager."""
        self.current_status = DegradationStatus()
        self.service_statuses: Dict[str, bool] = {}
        self.degradation_policies: Dict[str, Any] = {}
        logger.debug("GracefulDegradationManager initialized")
    
    def check_service_health(self, service_name: str) -> bool:
        """Check if a service is healthy."""
        return self.service_statuses.get(service_name, True)
    
    def set_service_status(self, service_name: str, is_healthy: bool):
        """Set the health status of a service."""
        previous_status = self.service_statuses.get(service_name, True)
        self.service_statuses[service_name] = is_healthy
        
        if previous_status != is_healthy:
            logger.info(f"Service {service_name} status changed: {is_healthy}")
            self._update_degradation_status()
    
    def _update_degradation_status(self):
        """Update overall degradation status based on service health."""
        unhealthy_services = [
            name for name, status in self.service_statuses.items() 
            if not status
        ]
        
        if not unhealthy_services:
            self.current_status = DegradationStatus(
                level=DegradationLevel.NORMAL,
                message="All services operational"
            )
        elif len(unhealthy_services) == 1:
            self.current_status = DegradationStatus(
                level=DegradationLevel.PARTIAL,
                affected_services=unhealthy_services,
                message=f"Service {unhealthy_services[0]} is degraded"
            )
        elif len(unhealthy_services) < len(self.service_statuses) / 2:
            self.current_status = DegradationStatus(
                level=DegradationLevel.DEGRADED,
                affected_services=unhealthy_services,
                message=f"{len(unhealthy_services)} services are degraded"
            )
        else:
            self.current_status = DegradationStatus(
                level=DegradationLevel.MINIMAL,
                affected_services=unhealthy_services,
                message="System in minimal operation mode"
            )
        
        logger.info(f"Degradation status updated: {self.current_status.level.value}")
    
    def get_degradation_status(self) -> DegradationStatus:
        """Get current degradation status."""
        return self.current_status
    
    def is_feature_available(self, feature_name: str) -> bool:
        """Check if a feature is available given current degradation level."""
        # Simple policy: most features available unless in minimal mode
        if self.current_status.level == DegradationLevel.MINIMAL:
            # Only core features available in minimal mode
            core_features = ["health_check", "basic_auth", "status"]
            return feature_name in core_features
        
        return True
    
    def get_degradation_message(self) -> str:
        """Get human-readable degradation status message."""
        return self.current_status.message
    
    def register_degradation_policy(self, service_name: str, policy: Dict[str, Any]):
        """Register degradation policy for a service."""
        self.degradation_policies[service_name] = policy
        logger.debug(f"Registered degradation policy for {service_name}")
    
    def apply_degradation_policy(self, service_name: str) -> Dict[str, Any]:
        """Apply degradation policy for a service."""
        policy = self.degradation_policies.get(service_name, {})
        return {
            "service": service_name,
            "degraded": not self.check_service_health(service_name),
            "fallback_enabled": policy.get("fallback_enabled", False),
            "degradation_level": self.current_status.level.value
        }


# Global instance
_degradation_manager: Optional[GracefulDegradationManager] = None


def get_degradation_manager() -> GracefulDegradationManager:
    """Get global degradation manager instance."""
    global _degradation_manager
    if _degradation_manager is None:
        _degradation_manager = GracefulDegradationManager()
    return _degradation_manager


# Export the global instance as degradation_manager for convenience
degradation_manager = get_degradation_manager()


__all__ = [
    'GracefulDegradationManager',
    'DegradationLevel',
    'DegradationStatus', 
    'degradation_manager',
    'get_degradation_manager'
]