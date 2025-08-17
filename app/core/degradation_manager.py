"""Manager for graceful service degradation.

This module contains the main degradation manager that coordinates
degradation across all registered services.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from app.core.degradation_types import (
    DegradationLevel,
    DegradationPolicy,
    DegradationStrategy,
    ServiceStatus,
    ServiceTier
)
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class GracefulDegradationManager:
    """Manager for graceful service degradation."""
    
    def __init__(self):
        """Initialize degradation manager."""
        self.services: Dict[str, ServiceStatus] = {}
        self.strategies: Dict[str, DegradationStrategy] = {}
        self.policies: Dict[str, DegradationPolicy] = {}
        self.global_degradation_level = DegradationLevel.NORMAL
        self._init_resource_thresholds()
    
    def _init_resource_thresholds(self) -> None:
        """Initialize resource monitoring thresholds."""
        self.resource_thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_percent': 90.0,
            'connection_count': 1000
        }
    
    def register_service(
        self,
        name: str,
        strategy: DegradationStrategy,
        policy: DegradationPolicy
    ) -> None:
        """Register a service for degradation management."""
        self.services[name] = self._create_service_status(name)
        self.strategies[name] = strategy
        self.policies[name] = policy
        logger.info(f"Registered service for degradation: {name}")
    
    def _create_service_status(self, name: str) -> ServiceStatus:
        """Create initial service status."""
        return ServiceStatus(
            name=name,
            is_healthy=True,
            degradation_level=DegradationLevel.NORMAL,
            last_check=datetime.now()
        )
    
    async def check_and_degrade_services(self) -> None:
        """Check all services and apply degradation if needed."""
        resource_usage = await self._get_resource_usage()
        await self._update_global_degradation_level(resource_usage)
        await self._apply_service_degradations()
    
    async def _update_global_degradation_level(
        self,
        resource_usage: Dict[str, float]
    ) -> None:
        """Update global degradation level based on resources."""
        new_global_level = self._calculate_global_degradation_level(resource_usage)
        if new_global_level != self.global_degradation_level:
            logger.info(f"Global degradation level changing: {self.global_degradation_level.value} -> {new_global_level.value}")
            self.global_degradation_level = new_global_level
    
    async def _apply_service_degradations(self) -> None:
        """Apply degradation to all registered services."""
        for service_name, service_status in self.services.items():
            await self._degrade_service_if_needed(service_name, service_status)
    
    async def degrade_service(
        self,
        service_name: str,
        level: DegradationLevel,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Manually degrade a specific service."""
        if service_name not in self.strategies:
            raise ValueError(f"Unknown service: {service_name}")
        
        strategy = self.strategies[service_name]
        service_status = self.services[service_name]
        logger.info(f"Degrading service {service_name} to {level.value}")
        return await self._execute_service_degradation(
            strategy, service_status, level, context or {}
        )
    
    async def _execute_service_degradation(
        self,
        strategy: DegradationStrategy,
        service_status: ServiceStatus,
        level: DegradationLevel,
        context: Dict[str, Any]
    ) -> Any:
        """Execute degradation for a service."""
        result = await strategy.degrade_to_level(level, context)
        service_status.degradation_level = level
        service_status.last_check = datetime.now()
        return result
    
    async def restore_service(self, service_name: str) -> bool:
        """Attempt to restore service to normal operation."""
        if service_name not in self.strategies:
            return False
        
        strategy = self.strategies[service_name]
        service_status = self.services[service_name]
        
        if await strategy.can_restore_service():
            self._restore_service_status(service_status, service_name)
            return True
        return False
    
    def _restore_service_status(
        self,
        service_status: ServiceStatus,
        service_name: str
    ) -> None:
        """Restore service status to normal."""
        logger.info(f"Restoring service {service_name} to normal")
        service_status.degradation_level = DegradationLevel.NORMAL
        service_status.is_healthy = True
        service_status.error_count = 0
        service_status.last_check = datetime.now()
    
    async def _degrade_service_if_needed(
        self,
        service_name: str,
        service_status: ServiceStatus
    ) -> None:
        """Check if service needs degradation and apply it."""
        policy = self.policies[service_name]
        target_level = self._calculate_target_degradation_level(
            service_name, service_status, policy
        )
        
        if target_level != service_status.degradation_level:
            await self.degrade_service(service_name, target_level)
    
    def _calculate_target_degradation_level(
        self,
        service_name: str,
        service_status: ServiceStatus,
        policy: DegradationPolicy
    ) -> DegradationLevel:
        """Calculate target degradation level for service."""
        base_level = self.global_degradation_level
        tier_adjusted_level = self._adjust_level_for_tier(base_level, policy.tier)
        return self._adjust_level_for_health(tier_adjusted_level, service_status)
    
    def _adjust_level_for_tier(
        self,
        level: DegradationLevel,
        tier: ServiceTier
    ) -> DegradationLevel:
        """Adjust degradation level based on service tier."""
        if tier == ServiceTier.CRITICAL:
            return self._reduce_degradation_for_critical(level)
        elif tier == ServiceTier.OPTIONAL:
            return self._increase_degradation_for_optional(level)
        return level
    
    def _reduce_degradation_for_critical(
        self,
        level: DegradationLevel
    ) -> DegradationLevel:
        """Reduce degradation for critical services."""
        if level == DegradationLevel.EMERGENCY:
            return DegradationLevel.MINIMAL
        return level
    
    def _increase_degradation_for_optional(
        self,
        level: DegradationLevel
    ) -> DegradationLevel:
        """Increase degradation for optional services."""
        if level == DegradationLevel.REDUCED:
            return DegradationLevel.MINIMAL
        elif level == DegradationLevel.MINIMAL:
            return DegradationLevel.EMERGENCY
        return level
    
    def _adjust_level_for_health(
        self,
        level: DegradationLevel,
        service_status: ServiceStatus
    ) -> DegradationLevel:
        """Adjust degradation level based on service health."""
        if service_status.error_count > 5:
            return DegradationLevel.MINIMAL
        elif service_status.error_count > 10:
            return DegradationLevel.EMERGENCY
        return level
    
    def _calculate_global_degradation_level(
        self,
        resource_usage: Dict[str, float]
    ) -> DegradationLevel:
        """Calculate global degradation level based on resources."""
        cpu_usage = resource_usage.get('cpu_percent', 0)
        memory_usage = resource_usage.get('memory_percent', 0)
        
        if cpu_usage > 95 or memory_usage > 95:
            return DegradationLevel.EMERGENCY
        elif cpu_usage > 85 or memory_usage > 90:
            return DegradationLevel.MINIMAL
        elif cpu_usage > 75 or memory_usage > 80:
            return DegradationLevel.REDUCED
        return DegradationLevel.NORMAL
    
    async def _get_resource_usage(self) -> Dict[str, float]:
        """Get current system resource usage."""
        try:
            return await self._get_psutil_resource_usage()
        except ImportError:
            return self._get_fallback_resource_usage()
    
    async def _get_psutil_resource_usage(self) -> Dict[str, float]:
        """Get resource usage using psutil."""
        import psutil
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent
        }
    
    def _get_fallback_resource_usage(self) -> Dict[str, float]:
        """Get fallback resource usage when psutil unavailable."""
        return {
            'cpu_percent': 50.0,
            'memory_percent': 60.0,
            'disk_percent': 70.0
        }
    
    def get_degradation_status(self) -> Dict[str, Any]:
        """Get current degradation status for all services."""
        return {
            'global_level': self.global_degradation_level.value,
            'services': self._get_all_service_statuses()
        }
    
    def _get_all_service_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status for all registered services."""
        return {
            name: {
                'healthy': status.is_healthy,
                'level': status.degradation_level.value,
                'error_count': status.error_count,
                'last_check': status.last_check.isoformat()
            }
            for name, status in self.services.items()
        }