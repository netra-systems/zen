"""Unified registry for all resilience components.

This module provides the central registry that coordinates:
- Circuit breakers, retry managers, and fallback chains
- Policy-driven component configuration
- Enterprise monitoring and health tracking
- Single point of access for all resilience operations

All functions are  <= 8 lines per MANDATORY requirements.
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, TypeVar

from netra_backend.app.core.resilience.circuit_breaker import (
    CircuitBreakerOpenError,
    UnifiedCircuitBreaker,
)
from netra_backend.app.core.resilience.fallback import (
    UnifiedFallbackChain,
    fallback_manager,
)
from netra_backend.app.core.resilience.monitor import HealthStatus, resilience_monitor
from netra_backend.app.core.resilience.policy import (
    EnvironmentType,
    ResiliencePolicy,
    policy_manager,
)
from netra_backend.app.core.resilience.retry_manager import (
    RetryExhaustedException,
    UnifiedRetryManager,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)
T = TypeVar('T')


@dataclass
class ServiceResilienceComponents:
    """Container for all resilience components of a service."""
    service_name: str
    circuit_breaker: UnifiedCircuitBreaker
    retry_manager: UnifiedRetryManager
    fallback_chain: Optional[UnifiedFallbackChain]
    policy: ResiliencePolicy
    enabled: bool = True


class UnifiedResilienceRegistry:
    """Enterprise resilience registry and orchestrator."""
    
    def __init__(self) -> None:
        self.services: Dict[str, ServiceResilienceComponents] = {}
        self.initialized = False
    
    async def initialize(self) -> None:
        """Initialize the resilience registry."""
        if self.initialized:
            logger.warning("Resilience registry already initialized")
            return
        
        await resilience_monitor.start_monitoring(interval_seconds=30.0)
        self.initialized = True
        logger.info("Unified resilience registry initialized")
    
    async def shutdown(self) -> None:
        """Shutdown the resilience registry."""
        await resilience_monitor.stop_monitoring()
        self.initialized = False
        logger.info("Unified resilience registry shutdown")
    
    def register_service(
        self, 
        service_name: str, 
        policy: ResiliencePolicy
    ) -> ServiceResilienceComponents:
        """Register service with complete resilience setup."""
        if service_name in self.services:
            return self._get_existing_service(service_name)
        
        return self._register_new_service(service_name, policy)
    
    def _get_existing_service(self, service_name: str) -> ServiceResilienceComponents:
        """Get existing registered service."""
        logger.warning(f"Service already registered: {service_name}")
        return self.services[service_name]
    
    def _register_new_service(
        self, 
        service_name: str, 
        policy: ResiliencePolicy
    ) -> ServiceResilienceComponents:
        """Register new service with components."""
        components = self._create_service_components(service_name, policy)
        self.services[service_name] = components
        self._setup_monitoring(service_name, policy)
        logger.info(f"Registered resilience components for: {service_name}")
        return components
    
    def _create_service_components(
        self, 
        service_name: str, 
        policy: ResiliencePolicy
    ) -> ServiceResilienceComponents:
        """Create all resilience components for service."""
        circuit_breaker = UnifiedCircuitBreaker(policy.circuit_config)
        retry_manager = UnifiedRetryManager(policy.retry_config)
        fallback_chain = self._create_fallback_chain(service_name, policy)
        
        return self._build_service_components(
            service_name, circuit_breaker, retry_manager, fallback_chain, policy
        )
    
    def _build_service_components(
        self, 
        service_name: str, 
        circuit_breaker: UnifiedCircuitBreaker, 
        retry_manager: UnifiedRetryManager, 
        fallback_chain: Optional[UnifiedFallbackChain], 
        policy: ResiliencePolicy
    ) -> ServiceResilienceComponents:
        """Build service components container."""
        return ServiceResilienceComponents(
            service_name=service_name,
            circuit_breaker=circuit_breaker,
            retry_manager=retry_manager,
            fallback_chain=fallback_chain,
            policy=policy,
            enabled=policy.enabled
        )
    
    def _create_fallback_chain(
        self, 
        service_name: str, 
        policy: ResiliencePolicy
    ) -> Optional[UnifiedFallbackChain]:
        """Create fallback chain for service if configured."""
        if not policy.fallback_configs:
            return None
        
        chain = fallback_manager.create_chain(service_name)
        for fallback_config in policy.fallback_configs:
            # Additional fallback handler creation would be here
            pass
        return chain
    
    def _setup_monitoring(self, service_name: str, policy: ResiliencePolicy) -> None:
        """Setup monitoring for service."""
        resilience_monitor.register_service(service_name)
        
        for threshold in policy.alert_thresholds:
            resilience_monitor.add_alert_threshold(service_name, threshold)
    
    async def execute_with_resilience(
        self, 
        service_name: str, 
        operation: Callable[[], T], 
        context: Optional[Dict[str, Any]] = None
    ) -> T:
        """Execute operation with full resilience protection."""
        components = self.services.get(service_name)
        if not components or not components.enabled:
            logger.debug(f"No resilience for {service_name}, executing directly")
            return await self._call_operation(operation)
        
        return await self._execute_with_full_protection(components, operation, context)
    
    async def _execute_with_full_protection(
        self, 
        components: ServiceResilienceComponents, 
        operation: Callable[[], T], 
        context: Optional[Dict[str, Any]]
    ) -> T:
        """Execute with circuit breaker, retry, and fallback protection."""
        try:
            return await components.retry_manager.execute_with_retry(
                lambda: components.circuit_breaker.call(operation), context
            )
        except (CircuitBreakerOpenError, RetryExhaustedException) as e:
            return await self._handle_resilience_failure(components, context, e)
    
    async def _handle_resilience_failure(
        self, 
        components: ServiceResilienceComponents, 
        context: Optional[Dict[str, Any]], 
        original_exception: Exception
    ) -> T:
        """Handle failure by attempting fallback."""
        if components.fallback_chain:
            return await self._execute_fallback(
                components, context, original_exception
            )
        
        raise original_exception
    
    async def _execute_fallback(
        self, 
        components: ServiceResilienceComponents, 
        context: Optional[Dict[str, Any]], 
        original_exception: Exception
    ) -> T:
        """Execute fallback chain with error handling."""
        try:
            return await components.fallback_chain.execute_fallback(
                context or {}, original_exception
            )
        except Exception as fallback_error:
            logger.error(f"Fallback failed for {components.service_name}: {fallback_error}")
            raise original_exception
    
    async def _call_operation(self, operation: Callable[[], T]) -> T:
        """Call operation handling both sync and async."""
        if asyncio.iscoroutinefunction(operation):
            return await operation()
        return operation()
    
    def get_service_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive status for service."""
        components = self.services.get(service_name)
        if not components:
            return None
        
        return self._build_service_status(service_name, components)
    
    def _build_service_status(
        self, 
        service_name: str, 
        components: ServiceResilienceComponents
    ) -> Dict[str, Any]:
        """Build comprehensive service status."""
        circuit_status = components.circuit_breaker.get_status()
        retry_metrics = components.retry_manager.get_metrics()
        health = resilience_monitor.get_service_health(service_name)
        
        return self._create_status_dict(
            service_name, components, circuit_status, retry_metrics, health
        )
    
    def _create_status_dict(
        self, 
        service_name: str, 
        components: ServiceResilienceComponents, 
        circuit_status: Dict[str, Any], 
        retry_metrics: Dict[str, Any], 
        health: Any
    ) -> Dict[str, Any]:
        """Create status dictionary."""
        return {
            "service_name": service_name,
            "enabled": components.enabled,
            "circuit_breaker": circuit_status,
            "retry_manager": retry_metrics,
            "health_status": health.status.value if health else "unknown",
            "policy_tier": components.policy.service_tier.value
        }
    
    def get_all_services_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status for all registered services."""
        status = {}
        for service_name in self.services.keys():
            service_status = self.get_service_status(service_name)
            if service_status:
                status[service_name] = service_status
        return status
    
    def update_service_policy(
        self, 
        service_name: str, 
        policy_updates: Dict[str, Any]
    ) -> bool:
        """Update policy for registered service."""
        components = self.services.get(service_name)
        if not components:
            return False
        
        success = policy_manager.update_policy(service_name, policy_updates)
        if success:
            self._apply_policy_updates(components, policy_updates)
        return success
    
    def _apply_policy_updates(
        self, 
        components: ServiceResilienceComponents, 
        updates: Dict[str, Any]
    ) -> None:
        """Apply policy updates to service components."""
        if "enabled" in updates:
            components.enabled = updates["enabled"]
        
        if "circuit" in updates:
            self._update_circuit_breaker(components, updates["circuit"])
        
        if "retry" in updates:
            self._update_retry_manager(components, updates["retry"])
    
    def _update_circuit_breaker(
        self, 
        components: ServiceResilienceComponents, 
        updates: Dict[str, Any]
    ) -> None:
        """Update circuit breaker configuration."""
        for key, value in updates.items():
            if hasattr(components.circuit_breaker.config, key):
                setattr(components.circuit_breaker.config, key, value)
    
    def _update_retry_manager(
        self, 
        components: ServiceResilienceComponents, 
        updates: Dict[str, Any]
    ) -> None:
        """Update retry manager configuration."""
        for key, value in updates.items():
            if hasattr(components.retry_manager.config, key):
                setattr(components.retry_manager.config, key, value)
    
    def enable_service(self, service_name: str) -> bool:
        """Enable resilience for service."""
        components = self.services.get(service_name)
        if components:
            components.enabled = True
            logger.info(f"Enabled resilience for: {service_name}")
            return True
        return False
    
    def disable_service(self, service_name: str) -> bool:
        """Disable resilience for service."""
        components = self.services.get(service_name)
        if components:
            components.enabled = False
            logger.info(f"Disabled resilience for: {service_name}")
            return True
        return False
    
    def unregister_service(self, service_name: str) -> bool:
        """Unregister service from resilience registry."""
        if service_name in self.services:
            del self.services[service_name]
            logger.info(f"Unregistered service: {service_name}")
            return True
        return False
    
    def report_metric(
        self, 
        service_name: str, 
        metric_name: str, 
        value: float
    ) -> None:
        """Report metric for service monitoring."""
        resilience_monitor.report_metric(service_name, metric_name, value)
    
    def get_system_health_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive system health dashboard."""
        system_summary = resilience_monitor.get_system_health_summary()
        policy_summary = policy_manager.get_policy_summary()
        service_count = len(self.services)
        
        return self._build_dashboard_dict(
            system_summary, policy_summary, service_count
        )
    
    def _build_dashboard_dict(
        self, 
        system_summary: Dict[str, Any], 
        policy_summary: Dict[str, Any], 
        service_count: int
    ) -> Dict[str, Any]:
        """Build system health dashboard dictionary."""
        return {
            "registry_status": "initialized" if self.initialized else "not_initialized",
            "total_registered_services": service_count,
            "enabled_services": self._count_enabled_services(),
            "system_health": system_summary,
            "policy_management": policy_summary,
            "monitoring_active": system_summary.get("monitoring_active", False)
        }
    
    def _count_enabled_services(self) -> int:
        """Count enabled services."""
        return sum(1 for s in self.services.values() if s.enabled)


# Global resilience registry instance
resilience_registry = UnifiedResilienceRegistry()


# Convenience functions for common operations
async def with_resilience(
    service_name: str, 
    operation: Callable[[], T], 
    context: Optional[Dict[str, Any]] = None
) -> T:
    """Execute operation with resilience protection."""
    return await resilience_registry.execute_with_resilience(
        service_name, operation, context
    )


def register_api_service(
    service_name: str, 
    environment: EnvironmentType = EnvironmentType.PRODUCTION
) -> ServiceResilienceComponents:
    """Register API service with appropriate policy."""
    from netra_backend.app.core.resilience.policy import create_api_service_policy
    policy = create_api_service_policy(service_name, environment)
    return resilience_registry.register_service(service_name, policy)


def register_database_service(
    service_name: str, 
    environment: EnvironmentType = EnvironmentType.PRODUCTION
) -> ServiceResilienceComponents:
    """Register database service with appropriate policy."""
    from netra_backend.app.core.resilience.policy import create_database_service_policy
    policy = create_database_service_policy(service_name, environment)
    return resilience_registry.register_service(service_name, policy)


def register_llm_service(
    service_name: str, 
    environment: EnvironmentType = EnvironmentType.PRODUCTION
) -> ServiceResilienceComponents:
    """Register LLM service with appropriate policy."""
    from netra_backend.app.core.resilience.policy import create_llm_service_policy
    policy = create_llm_service_policy(service_name, environment)
    return resilience_registry.register_service(service_name, policy)