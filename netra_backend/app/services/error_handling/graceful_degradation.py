"""
Graceful Degradation Manager - SSOT for Service Degradation Management

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise)
- Business Goal: Maintain service availability during partial system failures
- Value Impact: Ensures user experience continues even during infrastructure issues
- Strategic Impact: Critical for service reliability and customer retention
"""

import time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ServiceStatus(Enum):
    """Service status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE = "offline"


class DegradationLevel(Enum):
    """Levels of service degradation."""
    NONE = "none"
    MINOR = "minor"
    MODERATE = "moderate"  
    SEVERE = "severe"
    CRITICAL = "critical"


@dataclass
class ServiceHealthStatus:
    """Health status for a specific service."""
    service_name: str
    status: ServiceStatus
    degradation_level: DegradationLevel
    last_check: datetime
    error_count: int
    success_rate: float
    response_time_ms: float
    fallback_active: bool
    metadata: Dict[str, Any]


@dataclass
class DegradationStrategy:
    """Strategy for handling service degradation."""
    service_name: str
    degradation_level: DegradationLevel
    fallback_enabled: bool
    fallback_service: Optional[str]
    timeout_ms: int
    retry_count: int
    circuit_breaker_threshold: int


class GracefulDegradationManager:
    """SSOT Graceful Degradation Manager for service reliability.
    
    This class manages service health monitoring, degradation detection,
    and automatic fallback strategies to maintain system availability.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize graceful degradation manager.
        
        Args:
            config: Optional configuration for degradation policies
        """
        self.config = config or self._get_default_config()
        self._service_health: Dict[str, ServiceHealthStatus] = {}
        self._degradation_strategies: Dict[str, DegradationStrategy] = {}
        self._fallback_handlers: Dict[str, Callable] = {}
        
        logger.info("GracefulDegradationManager initialized")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default degradation configuration."""
        return {
            "health_check_interval": 30,  # seconds
            "degradation_threshold": 0.8,  # 80% success rate
            "critical_threshold": 0.5,     # 50% success rate
            "response_time_threshold": 5000,  # 5 seconds
            "enable_auto_fallback": True,
            "circuit_breaker_threshold": 5,
            "service_timeout": 30000  # 30 seconds
        }
    
    def register_service(
        self,
        service_name: str,
        fallback_handler: Optional[Callable] = None,
        degradation_strategy: Optional[DegradationStrategy] = None
    ) -> None:
        """Register a service for degradation management.
        
        Args:
            service_name: Name of the service to monitor
            fallback_handler: Optional fallback handler function
            degradation_strategy: Custom degradation strategy
        """
        # Initialize service health status
        self._service_health[service_name] = ServiceHealthStatus(
            service_name=service_name,
            status=ServiceStatus.HEALTHY,
            degradation_level=DegradationLevel.NONE,
            last_check=datetime.now(timezone.utc),
            error_count=0,
            success_rate=1.0,
            response_time_ms=0.0,
            fallback_active=False,
            metadata={}
        )
        
        # Set up degradation strategy
        if degradation_strategy:
            self._degradation_strategies[service_name] = degradation_strategy
        else:
            self._degradation_strategies[service_name] = DegradationStrategy(
                service_name=service_name,
                degradation_level=DegradationLevel.NONE,
                fallback_enabled=True,
                fallback_service=None,
                timeout_ms=self.config["service_timeout"],
                retry_count=3,
                circuit_breaker_threshold=self.config["circuit_breaker_threshold"]
            )
        
        # Register fallback handler
        if fallback_handler:
            self._fallback_handlers[service_name] = fallback_handler
        
        logger.info(f"Registered service for degradation management: {service_name}")
    
    def update_service_health(
        self,
        service_name: str,
        success: bool,
        response_time_ms: float = 0.0,
        error_details: Optional[str] = None
    ) -> None:
        """Update service health status based on operation result.
        
        Args:
            service_name: Name of the service
            success: Whether the operation was successful
            response_time_ms: Response time in milliseconds
            error_details: Optional error details
        """
        if service_name not in self._service_health:
            self.register_service(service_name)
        
        health = self._service_health[service_name]
        
        # Update metrics
        if not success:
            health.error_count += 1
        
        health.response_time_ms = (health.response_time_ms + response_time_ms) / 2
        health.last_check = datetime.now(timezone.utc)
        
        # Calculate success rate (simple moving average)
        if 'total_requests' not in health.metadata:
            health.metadata['total_requests'] = 0
            health.metadata['successful_requests'] = 0
        
        health.metadata['total_requests'] += 1
        if success:
            health.metadata['successful_requests'] += 1
        
        health.success_rate = (
            health.metadata['successful_requests'] / 
            health.metadata['total_requests']
        )
        
        # Update degradation level based on metrics
        self._update_degradation_level(service_name)
        
        # Store error details
        if error_details:
            if 'recent_errors' not in health.metadata:
                health.metadata['recent_errors'] = []
            health.metadata['recent_errors'].append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': error_details
            })
            # Keep only last 10 errors
            health.metadata['recent_errors'] = health.metadata['recent_errors'][-10:]
    
    def _update_degradation_level(self, service_name: str) -> None:
        """Update service degradation level based on current metrics."""
        health = self._service_health[service_name]
        
        # Determine degradation level
        if health.success_rate >= self.config["degradation_threshold"]:
            if health.response_time_ms < self.config["response_time_threshold"]:
                new_level = DegradationLevel.NONE
                new_status = ServiceStatus.HEALTHY
            else:
                new_level = DegradationLevel.MINOR
                new_status = ServiceStatus.DEGRADED
        elif health.success_rate >= self.config["critical_threshold"]:
            new_level = DegradationLevel.MODERATE
            new_status = ServiceStatus.DEGRADED
        elif health.success_rate >= 0.25:  # 25%
            new_level = DegradationLevel.SEVERE
            new_status = ServiceStatus.CRITICAL
        else:
            new_level = DegradationLevel.CRITICAL
            new_status = ServiceStatus.OFFLINE
        
        # Update status if changed
        if new_level != health.degradation_level or new_status != health.status:
            old_level = health.degradation_level
            old_status = health.status
            
            health.degradation_level = new_level
            health.status = new_status
            
            logger.warning(
                f"Service {service_name} degradation changed: "
                f"{old_status.value}({old_level.value})  ->  {new_status.value}({new_level.value})"
            )
            
            # Activate/deactivate fallback based on degradation
            self._manage_fallback_activation(service_name)
    
    def _manage_fallback_activation(self, service_name: str) -> None:
        """Manage fallback activation based on degradation level."""
        health = self._service_health[service_name]
        strategy = self._degradation_strategies.get(service_name)
        
        if not strategy or not strategy.fallback_enabled:
            return
        
        # Activate fallback for severe degradation
        should_activate = health.degradation_level in [
            DegradationLevel.SEVERE, 
            DegradationLevel.CRITICAL
        ]
        
        if should_activate and not health.fallback_active:
            health.fallback_active = True
            logger.warning(f"Activated fallback for service: {service_name}")
        elif not should_activate and health.fallback_active:
            health.fallback_active = False  
            logger.info(f"Deactivated fallback for service: {service_name}")
    
    def should_use_fallback(self, service_name: str) -> bool:
        """Check if fallback should be used for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            True if fallback should be used
        """
        if service_name not in self._service_health:
            return False
        
        health = self._service_health[service_name]
        return health.fallback_active
    
    async def execute_with_degradation_handling(
        self,
        service_name: str,
        primary_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute function with automatic degradation handling.
        
        Args:
            service_name: Name of the service
            primary_func: Primary function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result from primary function or fallback
        """
        start_time = time.time()
        
        try:
            # Check if we should use fallback immediately
            if self.should_use_fallback(service_name):
                return await self._execute_fallback(service_name, *args, **kwargs)
            
            # Execute primary function
            if hasattr(primary_func, '__call__'):
                if hasattr(primary_func, '__await__'):
                    result = await primary_func(*args, **kwargs)
                else:
                    result = primary_func(*args, **kwargs)
            else:
                raise ValueError(f"Invalid primary function for {service_name}")
            
            # Record success
            response_time = (time.time() - start_time) * 1000
            self.update_service_health(service_name, True, response_time)
            
            return result
            
        except Exception as e:
            # Record failure
            response_time = (time.time() - start_time) * 1000
            self.update_service_health(service_name, False, response_time, str(e))
            
            # Try fallback if available
            if service_name in self._fallback_handlers:
                logger.warning(f"Primary function failed for {service_name}, using fallback: {e}")
                return await self._execute_fallback(service_name, *args, **kwargs)
            else:
                # Re-raise if no fallback available
                raise
    
    async def _execute_fallback(self, service_name: str, *args, **kwargs) -> Any:
        """Execute fallback handler for a service."""
        if service_name not in self._fallback_handlers:
            raise RuntimeError(f"No fallback handler registered for {service_name}")
        
        fallback_handler = self._fallback_handlers[service_name]
        
        try:
            if hasattr(fallback_handler, '__await__'):
                return await fallback_handler(*args, **kwargs)
            else:
                return fallback_handler(*args, **kwargs)
        except Exception as e:
            logger.error(f"Fallback handler failed for {service_name}: {e}")
            raise
    
    def get_service_health(self, service_name: str) -> Optional[ServiceHealthStatus]:
        """Get health status for a specific service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            ServiceHealthStatus or None if not found
        """
        return self._service_health.get(service_name)
    
    def get_all_service_health(self) -> Dict[str, ServiceHealthStatus]:
        """Get health status for all registered services.
        
        Returns:
            Dictionary of service names to health status
        """
        return self._service_health.copy()
    
    def get_degraded_services(self) -> List[str]:
        """Get list of services currently in degraded state.
        
        Returns:
            List of service names with degraded status
        """
        return [
            name for name, health in self._service_health.items()
            if health.status in [ServiceStatus.DEGRADED, ServiceStatus.CRITICAL, ServiceStatus.OFFLINE]
        ]
    
    def reset_service_health(self, service_name: str) -> None:
        """Reset health metrics for a service.
        
        Args:
            service_name: Name of the service to reset
        """
        if service_name in self._service_health:
            health = self._service_health[service_name]
            health.error_count = 0
            health.success_rate = 1.0
            health.response_time_ms = 0.0
            health.fallback_active = False
            health.status = ServiceStatus.HEALTHY
            health.degradation_level = DegradationLevel.NONE
            health.metadata.clear()
            
            logger.info(f"Reset health metrics for service: {service_name}")


# Export for test compatibility
__all__ = [
    'GracefulDegradationManager',
    'ServiceHealthStatus',
    'DegradationStrategy',
    'ServiceStatus',
    'DegradationLevel'
]