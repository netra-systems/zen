"""
Migration Adapters for Reliability Manager Consolidation

Provides backward compatibility adapters and migration helpers to allow
existing code to gradually transition to the unified reliability manager
without breaking changes.

Business Value: Enables seamless migration with zero downtime and maintains
existing functionality while consolidating duplicate implementations.
"""

import asyncio
import warnings
from typing import Any, Awaitable, Callable, Dict, Optional, TYPE_CHECKING

from netra_backend.app.core.reliability.unified_reliability_manager import (
    UnifiedReliabilityManager,
    get_reliability_manager
)
from netra_backend.app.schemas.shared_types import RetryConfig
from netra_backend.app.logging_config import central_logger

if TYPE_CHECKING:
    from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
    from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig
    from netra_backend.app.core.circuit_breaker import CircuitConfig
    from netra_backend.app.websocket_core.manager import WebSocketManager

logger = central_logger.get_logger(__name__)


class ReliabilityManagerAdapter:
    """
    Backward compatibility adapter for the original ReliabilityManager.
    
    Provides the same interface but delegates to UnifiedReliabilityManager.
    This allows existing agent code to work without changes while using
    the new consolidated reliability infrastructure.
    """
    
    def __init__(
        self, 
        circuit_breaker_config: 'CircuitBreakerConfig',
        retry_config: RetryConfig,
        websocket_manager: Optional['WebSocketManager'] = None
    ):
        warnings.warn(
            "ReliabilityManager is deprecated. Use UnifiedReliabilityManager directly.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Convert legacy config to new format
        service_name = getattr(circuit_breaker_config, 'name', 'legacy_service')
        
        # Get or create unified manager
        self._unified_manager = get_reliability_manager(
            service_name=service_name,
            retry_config=retry_config,
            websocket_manager=websocket_manager
        )
        
        # Store original configs for compatibility methods
        self.circuit_breaker_config = circuit_breaker_config
        self.retry_config = retry_config
        
        logger.info(f"Created ReliabilityManagerAdapter for {service_name}")
    
    async def execute_with_reliability(
        self, 
        context: 'ExecutionContext',
        execute_func: Callable[[], Awaitable['ExecutionResult']]
    ) -> 'ExecutionResult':
        """Execute with reliability patterns - legacy interface."""
        try:
            # Convert to new interface
            result = await self._unified_manager.execute_with_reliability(
                operation=execute_func,
                operation_name=getattr(context, 'operation_name', 'legacy_operation'),
                context=context,
                emit_events=True  # Enable WebSocket events
            )
            return result
        except Exception as e:
            # Create legacy-compatible error result
            return self._create_legacy_error_result(context, e)
    
    def _create_legacy_error_result(
        self, 
        context: 'ExecutionContext', 
        error: Exception
    ) -> 'ExecutionResult':
        """Create legacy-compatible error result."""
        from netra_backend.app.agents.base.interface import ExecutionResult
        from netra_backend.app.schemas.core_enums import ExecutionStatus
        
        execution_time = 0.0
        if hasattr(context, 'start_time') and context.start_time:
            import time
            execution_time = (time.time() - context.start_time) * 1000
        
        return ExecutionResult(
            success=False,
            status=ExecutionStatus.FAILED,
            error=str(error),
            execution_time_ms=execution_time,
            retry_count=getattr(context, 'retry_count', 0),
            metrics={
                "error_type": type(error).__name__,
                "adapter_used": "ReliabilityManagerAdapter"
            }
        )
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status - legacy interface."""
        status = self._unified_manager.get_health_status()
        
        # Add legacy-compatible fields
        status['retry_config'] = {
            'max_retries': self.retry_config.max_retries,
            'base_delay': self.retry_config.base_delay,
            'max_delay': self.retry_config.max_delay
        }
        
        return status
    
    def reset_health_tracking(self) -> None:
        """Reset health tracking - legacy interface."""
        self._unified_manager.reset_health_tracking()


class AgentReliabilityWrapperAdapter:
    """
    Backward compatibility adapter for AgentReliabilityWrapper.
    
    Maintains the same interface while using the unified reliability manager
    underneath for consistency and better functionality.
    """
    
    def __init__(
        self,
        agent_name: str,
        circuit_breaker_config: Optional['CircuitConfig'] = None,
        retry_config: Optional[RetryConfig] = None,
        websocket_manager: Optional['WebSocketManager'] = None
    ):
        warnings.warn(
            "AgentReliabilityWrapper is deprecated. Use UnifiedReliabilityManager directly.",
            DeprecationWarning,
            stacklevel=2
        )
        
        self.agent_name = agent_name
        
        # Use default retry config if none provided
        if retry_config is None:
            retry_config = RetryConfig()
        
        # Get or create unified manager
        self._unified_manager = get_reliability_manager(
            service_name=agent_name,
            retry_config=retry_config,
            websocket_manager=websocket_manager
        )
        
        logger.info(f"Created AgentReliabilityWrapperAdapter for {agent_name}")
    
    async def execute_safely(
        self,
        operation: Callable[[], Awaitable[Any]],
        operation_name: str,
        fallback: Optional[Callable[[], Awaitable[Any]]] = None,
        timeout: Optional[float] = None
    ) -> Any:
        """Execute operation safely - legacy interface."""
        return await self._unified_manager.execute_with_reliability(
            operation=operation,
            operation_name=operation_name,
            fallback=fallback,
            timeout=timeout,
            emit_events=False  # Legacy mode doesn't emit events
        )
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status - legacy interface."""
        status = self._unified_manager.get_health_status()
        
        # Restructure for legacy compatibility
        legacy_status = {
            "agent_name": self.agent_name,
            "circuit_breaker": status.get("circuit_breaker", {}),
            "recent_errors": status.get("recent_errors", 0),
            "total_tracked_errors": status.get("total_tracked_errors", 0),
            "last_error": None,  # Would need to implement if needed
            "health_score": status.get("health_score", 1.0)
        }
        
        return legacy_status


class RetryManagerAdapter:
    """
    Adapter for individual retry managers that use the old interface.
    
    Many services have their own RetryManager implementations. This adapter
    allows them to use the unified retry logic without code changes.
    """
    
    def __init__(self, retry_config: RetryConfig, service_name: str = "legacy_retry"):
        warnings.warn(
            "Individual RetryManager is deprecated. Use UnifiedReliabilityManager.",
            DeprecationWarning,
            stacklevel=2
        )
        
        self.config = retry_config
        self.service_name = service_name
        
        # Get unified manager for retry functionality
        self._unified_manager = get_reliability_manager(
            service_name=service_name,
            retry_config=retry_config
        )
    
    async def execute_with_retry(
        self,
        operation: Callable[[], Awaitable[Any]],
        context: Optional[Any] = None
    ) -> Any:
        """Execute with retry - legacy interface."""
        operation_name = "legacy_retry_operation"
        
        if context:
            # Extract operation name from context if available
            if hasattr(context, 'operation_name'):
                operation_name = context.operation_name
            elif hasattr(context, 'agent_name'):
                operation_name = f"{context.agent_name}_operation"
        
        return await self._unified_manager.execute_with_reliability(
            operation=operation,
            operation_name=operation_name,
            emit_events=False  # Legacy retry doesn't emit events
        )


# Global migration registry to track adapters
_migration_registry: Dict[str, Any] = {}


def create_legacy_reliability_manager(
    circuit_breaker_config: 'CircuitBreakerConfig',
    retry_config: RetryConfig,
    websocket_manager: Optional['WebSocketManager'] = None
) -> ReliabilityManagerAdapter:
    """
    Factory function to create legacy ReliabilityManager adapter.
    
    This function provides a drop-in replacement for the old ReliabilityManager
    constructor while using the new unified infrastructure.
    """
    service_name = getattr(circuit_breaker_config, 'name', 'legacy_reliability')
    
    # Track in migration registry
    _migration_registry[f"reliability_{service_name}"] = {
        'type': 'ReliabilityManagerAdapter',
        'service_name': service_name,
        'created_at': asyncio.get_event_loop().time()
    }
    
    return ReliabilityManagerAdapter(
        circuit_breaker_config,
        retry_config,
        websocket_manager
    )


def create_legacy_agent_wrapper(
    agent_name: str,
    circuit_breaker_config: Optional['CircuitConfig'] = None,
    retry_config: Optional[RetryConfig] = None,
    websocket_manager: Optional['WebSocketManager'] = None
) -> AgentReliabilityWrapperAdapter:
    """
    Factory function to create legacy AgentReliabilityWrapper adapter.
    
    Provides backward compatibility for agents using the old wrapper interface.
    """
    # Track in migration registry
    _migration_registry[f"agent_wrapper_{agent_name}"] = {
        'type': 'AgentReliabilityWrapperAdapter',
        'agent_name': agent_name,
        'created_at': asyncio.get_event_loop().time()
    }
    
    return AgentReliabilityWrapperAdapter(
        agent_name,
        circuit_breaker_config,
        retry_config,
        websocket_manager
    )


def create_legacy_retry_manager(
    retry_config: RetryConfig,
    service_name: str = "legacy_retry"
) -> RetryManagerAdapter:
    """
    Factory function to create legacy RetryManager adapter.
    
    For services that only need retry functionality without full reliability management.
    """
    # Track in migration registry
    _migration_registry[f"retry_{service_name}"] = {
        'type': 'RetryManagerAdapter',
        'service_name': service_name,
        'created_at': asyncio.get_event_loop().time()
    }
    
    return RetryManagerAdapter(retry_config, service_name)


def get_migration_status() -> Dict[str, Any]:
    """
    Get status of ongoing migration to unified reliability manager.
    
    Useful for tracking which services are still using legacy adapters
    and planning complete migration.
    """
    adapter_counts = {}
    for key, info in _migration_registry.items():
        adapter_type = info['type']
        adapter_counts[adapter_type] = adapter_counts.get(adapter_type, 0) + 1
    
    return {
        "total_adapters": len(_migration_registry),
        "adapter_breakdown": adapter_counts,
        "services_using_adapters": list(_migration_registry.keys()),
        "migration_complete": len(_migration_registry) == 0
    }


def log_migration_warnings() -> None:
    """
    Log warnings about services still using legacy adapters.
    
    Should be called periodically to remind about completing migration.
    """
    status = get_migration_status()
    
    if status["total_adapters"] > 0:
        logger.warning(
            f"Migration incomplete: {status['total_adapters']} services still using legacy adapters. "
            f"Services: {', '.join(status['services_using_adapters'])}"
        )
        
        for adapter_type, count in status["adapter_breakdown"].items():
            logger.info(f"  - {adapter_type}: {count} instances")
    else:
        logger.info("Migration complete: All services using UnifiedReliabilityManager")


# Convenience imports for backward compatibility
# These allow existing imports to continue working during migration
def ReliabilityManager(*args, **kwargs):
    """Legacy ReliabilityManager constructor - returns adapter."""
    return create_legacy_reliability_manager(*args, **kwargs)


def AgentReliabilityWrapper(*args, **kwargs):
    """Legacy AgentReliabilityWrapper constructor - returns adapter.""" 
    return create_legacy_agent_wrapper(*args, **kwargs)


def RetryManager(*args, **kwargs):
    """Legacy RetryManager constructor - returns adapter."""
    # Handle different call patterns
    if len(args) >= 1 and hasattr(args[0], 'max_retries'):
        return create_legacy_retry_manager(args[0], kwargs.get('service_name', 'legacy_retry'))
    else:
        # Fallback for other calling patterns
        retry_config = kwargs.get('retry_config', RetryConfig())
        service_name = kwargs.get('service_name', 'legacy_retry')
        return create_legacy_retry_manager(retry_config, service_name)