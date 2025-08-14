"""Graceful degradation strategies for system resilience.

Provides mechanisms to gracefully degrade functionality when system components
fail, ensuring core operations continue with reduced but acceptable performance.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from app.core.error_recovery import OperationType
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DegradationLevel(Enum):
    """Levels of service degradation."""
    NORMAL = "normal"
    REDUCED = "reduced"
    MINIMAL = "minimal"
    EMERGENCY = "emergency"


class ServiceTier(Enum):
    """Service tier priorities."""
    CRITICAL = "critical"    # Must maintain
    IMPORTANT = "important"  # Degrade if necessary
    OPTIONAL = "optional"    # Can disable
    AUXILIARY = "auxiliary"  # First to disable


@dataclass
class DegradationPolicy:
    """Policy for degrading a service."""
    service_name: str
    tier: ServiceTier
    degradation_levels: Dict[DegradationLevel, Callable]
    recovery_threshold: float = 0.8
    timeout_seconds: int = 300


@dataclass
class ServiceStatus:
    """Status of a service component."""
    name: str
    is_healthy: bool
    degradation_level: DegradationLevel
    last_check: datetime
    error_count: int = 0
    response_time: float = 0.0


class DegradationStrategy(ABC):
    """Abstract base for degradation strategies."""
    
    @abstractmethod
    async def degrade_to_level(
        self,
        level: DegradationLevel,
        context: Dict[str, Any]
    ) -> Any:
        """Degrade service to specified level."""
        pass
    
    @abstractmethod
    async def can_restore_service(self) -> bool:
        """Check if service can be restored to normal."""
        pass


class DatabaseDegradationStrategy(DegradationStrategy):
    """Degradation strategy for database operations."""
    
    def __init__(self, read_replicas: List[str], cache_manager):
        """Initialize with read replicas and cache."""
        self.read_replicas = read_replicas
        self.cache_manager = cache_manager
        self.current_replica_index = 0
    
    async def degrade_to_level(
        self,
        level: DegradationLevel,
        context: Dict[str, Any]
    ) -> Any:
        """Degrade database operations."""
        operation = context.get('operation', 'read')
        
        if level == DegradationLevel.REDUCED:
            return await self._use_read_replica(context)
        elif level == DegradationLevel.MINIMAL:
            return await self._use_cache_only(context)
        elif level == DegradationLevel.EMERGENCY:
            return await self._return_default_data(context)
        
        return None
    
    async def can_restore_service(self) -> bool:
        """Check if primary database is available."""
        try:
            # Simulate primary DB health check
            await asyncio.sleep(0.1)
            return True  # Placeholder
        except Exception:
            return False
    
    async def _use_read_replica(self, context: Dict[str, Any]) -> Any:
        """Use read replica for operations."""
        replica = self.read_replicas[self.current_replica_index]
        self.current_replica_index = (
            (self.current_replica_index + 1) % len(self.read_replicas)
        )
        
        logger.info(f"Using read replica: {replica}")
        return {'data': 'replica_data', 'source': 'replica'}
    
    async def _use_cache_only(self, context: Dict[str, Any]) -> Any:
        """Use cached data only."""
        cache_key = context.get('cache_key', 'default')
        
        try:
            cached_data = await self.cache_manager.get(cache_key)
            if cached_data:
                logger.info("Serving from cache only")
                return {'data': cached_data, 'source': 'cache', 'stale': True}
        except Exception as e:
            logger.warning(f"Cache access failed: {e}")
        
        return await self._return_default_data(context)
    
    async def _return_default_data(self, context: Dict[str, Any]) -> Any:
        """Return default/static data."""
        logger.warning("Returning default data due to database unavailability")
        return {
            'data': {'status': 'service_degraded'},
            'source': 'default',
            'message': 'Service temporarily degraded'
        }


class LLMDegradationStrategy(DegradationStrategy):
    """Degradation strategy for LLM operations."""
    
    def __init__(self, fallback_models: List[str], template_responses: Dict[str, str]):
        """Initialize with fallback models and templates."""
        self.fallback_models = fallback_models
        self.template_responses = template_responses
        self.current_model_index = 0
    
    async def degrade_to_level(
        self,
        level: DegradationLevel,
        context: Dict[str, Any]
    ) -> Any:
        """Degrade LLM operations."""
        if level == DegradationLevel.REDUCED:
            return await self._use_smaller_model(context)
        elif level == DegradationLevel.MINIMAL:
            return await self._use_template_response(context)
        elif level == DegradationLevel.EMERGENCY:
            return await self._return_error_message(context)
        
        return None
    
    async def can_restore_service(self) -> bool:
        """Check if primary LLM is available."""
        try:
            # Simulate LLM health check
            await asyncio.sleep(0.1)
            return True  # Placeholder
        except Exception:
            return False
    
    async def _use_smaller_model(self, context: Dict[str, Any]) -> Any:
        """Use smaller/faster model."""
        if self.fallback_models:
            model = self.fallback_models[self.current_model_index]
            self.current_model_index = (
                (self.current_model_index + 1) % len(self.fallback_models)
            )
            
            logger.info(f"Using fallback model: {model}")
            return {
                'response': 'Simplified response from fallback model',
                'model': model,
                'degraded': True
            }
        
        return await self._use_template_response(context)
    
    async def _use_template_response(self, context: Dict[str, Any]) -> Any:
        """Use pre-defined template responses."""
        intent = context.get('intent', 'general')
        template = self.template_responses.get(intent, self.template_responses.get('general'))
        
        logger.info("Using template response due to LLM unavailability")
        return {
            'response': template,
            'source': 'template',
            'degraded': True
        }
    
    async def _return_error_message(self, context: Dict[str, Any]) -> Any:
        """Return service unavailable message."""
        return {
            'response': 'I apologize, but AI services are temporarily unavailable. Please try again later.',
            'source': 'error',
            'service_available': False
        }


class WebSocketDegradationStrategy(DegradationStrategy):
    """Degradation strategy for WebSocket operations."""
    
    def __init__(self, polling_fallback: bool = True):
        """Initialize with polling fallback option."""
        self.polling_fallback = polling_fallback
        self.degraded_connections: Set[str] = set()
    
    async def degrade_to_level(
        self,
        level: DegradationLevel,
        context: Dict[str, Any]
    ) -> Any:
        """Degrade WebSocket operations."""
        connection_id = context.get('connection_id', 'unknown')
        
        if level == DegradationLevel.REDUCED:
            return await self._reduce_message_frequency(context)
        elif level == DegradationLevel.MINIMAL:
            return await self._switch_to_polling(context)
        elif level == DegradationLevel.EMERGENCY:
            return await self._disable_real_time_updates(context)
        
        return None
    
    async def can_restore_service(self) -> bool:
        """Check if WebSocket service can be restored."""
        try:
            # Simulate WebSocket health check
            await asyncio.sleep(0.1)
            return True  # Placeholder
        except Exception:
            return False
    
    async def _reduce_message_frequency(self, context: Dict[str, Any]) -> Any:
        """Reduce message frequency to conserve resources."""
        connection_id = context.get('connection_id')
        self.degraded_connections.add(connection_id)
        
        logger.info(f"Reducing message frequency for connection {connection_id}")
        return {
            'action': 'frequency_reduced',
            'interval': 5.0,  # Reduced frequency
            'degraded': True
        }
    
    async def _switch_to_polling(self, context: Dict[str, Any]) -> Any:
        """Switch to HTTP polling instead of WebSocket."""
        if self.polling_fallback:
            logger.info("Switching to HTTP polling fallback")
            return {
                'action': 'polling_fallback',
                'poll_interval': 10.0,
                'endpoint': '/api/poll'
            }
        
        return await self._disable_real_time_updates(context)
    
    async def _disable_real_time_updates(self, context: Dict[str, Any]) -> Any:
        """Disable real-time updates entirely."""
        logger.warning("Disabling real-time updates")
        return {
            'action': 'disabled',
            'message': 'Real-time updates temporarily disabled'
        }


class GracefulDegradationManager:
    """Manager for graceful service degradation."""
    
    def __init__(self):
        """Initialize degradation manager."""
        self.services: Dict[str, ServiceStatus] = {}
        self.strategies: Dict[str, DegradationStrategy] = {}
        self.policies: Dict[str, DegradationPolicy] = {}
        self.global_degradation_level = DegradationLevel.NORMAL
        
        # Resource monitoring
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
        self.services[name] = ServiceStatus(
            name=name,
            is_healthy=True,
            degradation_level=DegradationLevel.NORMAL,
            last_check=datetime.now()
        )
        self.strategies[name] = strategy
        self.policies[name] = policy
        
        logger.info(f"Registered service for degradation: {name}")
    
    async def check_and_degrade_services(self) -> None:
        """Check all services and apply degradation if needed."""
        resource_usage = await self._get_resource_usage()
        
        # Determine global degradation level
        new_global_level = self._calculate_global_degradation_level(resource_usage)
        
        if new_global_level != self.global_degradation_level:
            logger.info(f"Global degradation level changing: {self.global_degradation_level.value} -> {new_global_level.value}")
            self.global_degradation_level = new_global_level
        
        # Apply degradation to services
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
        
        result = await strategy.degrade_to_level(level, context or {})
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
            logger.info(f"Restoring service {service_name} to normal")
            service_status.degradation_level = DegradationLevel.NORMAL
            service_status.is_healthy = True
            service_status.error_count = 0
            service_status.last_check = datetime.now()
            return True
        
        return False
    
    async def _degrade_service_if_needed(
        self,
        service_name: str,
        service_status: ServiceStatus
    ) -> None:
        """Check if service needs degradation."""
        policy = self.policies[service_name]
        
        # Calculate target degradation level
        target_level = self._calculate_target_degradation_level(
            service_name, service_status, policy
        )
        
        # Apply degradation if needed
        if target_level != service_status.degradation_level:
            await self.degrade_service(service_name, target_level)
    
    def _calculate_target_degradation_level(
        self,
        service_name: str,
        service_status: ServiceStatus,
        policy: DegradationPolicy
    ) -> DegradationLevel:
        """Calculate target degradation level for service."""
        # Start with global level
        target_level = self.global_degradation_level
        
        # Adjust based on service tier
        if policy.tier == ServiceTier.CRITICAL:
            # Critical services degrade less aggressively
            if target_level == DegradationLevel.EMERGENCY:
                target_level = DegradationLevel.MINIMAL
        elif policy.tier == ServiceTier.OPTIONAL:
            # Optional services degrade more aggressively
            if target_level == DegradationLevel.REDUCED:
                target_level = DegradationLevel.MINIMAL
            elif target_level == DegradationLevel.MINIMAL:
                target_level = DegradationLevel.EMERGENCY
        
        # Consider service-specific health
        if service_status.error_count > 5:
            target_level = DegradationLevel.MINIMAL
        elif service_status.error_count > 10:
            target_level = DegradationLevel.EMERGENCY
        
        return target_level
    
    def _calculate_global_degradation_level(
        self,
        resource_usage: Dict[str, float]
    ) -> DegradationLevel:
        """Calculate global degradation level based on resources."""
        cpu_usage = resource_usage.get('cpu_percent', 0)
        memory_usage = resource_usage.get('memory_percent', 0)
        
        # Emergency level - system critical
        if cpu_usage > 95 or memory_usage > 95:
            return DegradationLevel.EMERGENCY
        
        # Minimal level - high resource usage
        if cpu_usage > 85 or memory_usage > 90:
            return DegradationLevel.MINIMAL
        
        # Reduced level - moderate resource usage
        if cpu_usage > 75 or memory_usage > 80:
            return DegradationLevel.REDUCED
        
        return DegradationLevel.NORMAL
    
    async def _get_resource_usage(self) -> Dict[str, float]:
        """Get current system resource usage."""
        try:
            import psutil
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent
            }
        except ImportError:
            # Fallback if psutil not available
            return {
                'cpu_percent': 50.0,
                'memory_percent': 60.0,
                'disk_percent': 70.0
            }
    
    def get_degradation_status(self) -> Dict[str, Any]:
        """Get current degradation status."""
        return {
            'global_level': self.global_degradation_level.value,
            'services': {
                name: {
                    'healthy': status.is_healthy,
                    'level': status.degradation_level.value,
                    'error_count': status.error_count,
                    'last_check': status.last_check.isoformat()
                }
                for name, status in self.services.items()
            }
        }


# Global degradation manager instance
degradation_manager = GracefulDegradationManager()


# Common degradation strategies for standard services
def create_database_degradation_strategy(
    read_replicas: List[str],
    cache_manager
) -> DatabaseDegradationStrategy:
    """Create database degradation strategy."""
    return DatabaseDegradationStrategy(read_replicas, cache_manager)


def create_llm_degradation_strategy(
    fallback_models: List[str],
    template_responses: Dict[str, str]
) -> LLMDegradationStrategy:
    """Create LLM degradation strategy."""
    return LLMDegradationStrategy(fallback_models, template_responses)


def create_websocket_degradation_strategy(
    polling_fallback: bool = True
) -> WebSocketDegradationStrategy:
    """Create WebSocket degradation strategy."""
    return WebSocketDegradationStrategy(polling_fallback)