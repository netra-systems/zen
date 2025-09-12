"""DEPRECATED: Core circuit breaker implementation - MIGRATED TO UnifiedCircuitBreaker.

 WARNING: [U+FE0F]  MIGRATION TO UNIFIED CIRCUIT BREAKER  WARNING: [U+FE0F]

This module now serves as a compatibility wrapper around UnifiedCircuitBreaker.
All functionality has been migrated to the unified SSOT implementation.

For new code, use:
    from netra_backend.app.core.resilience.unified_circuit_breaker import UnifiedCircuitBreaker

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide backward compatibility during SSOT migration
- Value Impact: Ensures existing code works while consolidating implementations
- Strategic Impact: Unified resilience foundation with legacy support

All functions adhere to  <= 8 line complexity limit per MANDATORY requirements.
"""

import asyncio
import time
import warnings
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar

from netra_backend.app.core.circuit_breaker_types import (
    CircuitBreakerOpenError,
    CircuitConfig,
    CircuitMetrics,
    CircuitState,
)
from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker,
    UnifiedCircuitConfig,
    get_unified_circuit_breaker_manager,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)
T = TypeVar('T')


class CircuitBreaker:
    """DEPRECATED: Core circuit breaker - now delegates to UnifiedCircuitBreaker.
    
    This is a compatibility wrapper around UnifiedCircuitBreaker that maintains
    the legacy interface while using the unified SSOT implementation internally.
    """
    
    def __init__(self, config: CircuitConfig) -> None:
        """Initialize circuit breaker with provided configuration - delegates to UnifiedCircuitBreaker."""
        warnings.warn(
            "CircuitBreaker from circuit_breaker_core is deprecated. "
            "Use UnifiedCircuitBreaker directly for new code.",
            DeprecationWarning,
            stacklevel=2
        )
        
        self.config = config
        
        # Convert legacy config to unified config
        unified_config = self._convert_to_unified_config(config)
        manager = get_unified_circuit_breaker_manager()
        self._unified_breaker = manager.create_circuit_breaker(config.name, unified_config)
        
        # Legacy compatibility properties
        self.metrics = CircuitMetrics()
        self.last_failure_time: Optional[float] = None
        self.last_success_time: Optional[float] = None
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        
    def _convert_to_unified_config(self, config: CircuitConfig) -> UnifiedCircuitConfig:
        """Convert legacy CircuitConfig to UnifiedCircuitConfig."""
        return UnifiedCircuitConfig(
            name=config.name,
            failure_threshold=config.failure_threshold,
            recovery_timeout=config.recovery_timeout,
            success_threshold=getattr(config, 'success_threshold', 3),  # Default success threshold
            timeout_seconds=config.timeout_seconds,
            half_open_max_calls=config.half_open_max_calls,
            adaptive_threshold=getattr(config, 'adaptive_threshold', False),
            slow_call_threshold=getattr(config, 'slow_call_threshold', 5.0),
            sliding_window_size=getattr(config, 'sliding_window_size', 10),
            # Legacy compatibility: disable advanced features for predictable behavior
            exponential_backoff=False,
            jitter=False,
        )
        
    async def call(self, operation: Callable[..., T], *args, **kwargs) -> T:
        """Execute operation with circuit breaker protection - delegates to unified implementation."""
        try:
            result = await self._unified_breaker.call(operation, *args, **kwargs)
            self._update_legacy_metrics_on_success()
            return result
        except Exception as e:
            self._update_legacy_metrics_on_failure(str(type(e).__name__))
            # Re-raise the exception from unified breaker (already proper type)
            raise
        
    def can_execute(self) -> bool:
        """Check if operation can be executed - delegates to unified breaker."""
        return self._unified_breaker.can_execute()
            
    @property
    def state(self) -> CircuitState:
        """Get current circuit state from unified breaker."""
        return self._unified_breaker.state
        
    @state.setter
    def state(self, value: CircuitState) -> None:
        """Set circuit state - legacy compatibility."""
        # For legacy compatibility, but state is managed by unified breaker
        pass
        
    def _update_legacy_metrics_on_success(self) -> None:
        """Update legacy metrics for backward compatibility."""
        self.metrics.total_calls += 1
        self.metrics.successful_calls += 1
        self._consecutive_successes += 1
        self._consecutive_failures = 0
        self.last_success_time = time.time()
        
    def _update_legacy_metrics_on_failure(self, error_type: str) -> None:
        """Update legacy metrics on failure for backward compatibility."""
        self.metrics.total_calls += 1
        self.metrics.failed_calls += 1
        self._consecutive_failures += 1
        self._consecutive_successes = 0
        self.last_failure_time = time.time()
            
    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery - legacy compatibility."""
        if not self.last_failure_time:
            return False
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.config.recovery_timeout
            
    def _record_success(self, response_time: float) -> None:
        """Record successful operation execution - legacy compatibility."""
        self._update_legacy_metrics_on_success()
        # State transitions are handled by unified breaker
        
    def _handle_success_state_transition(self) -> None:
        """Handle state transitions - delegated to unified breaker."""
        # State transitions are handled by unified breaker
        pass
            
    def _record_failure(self, response_time: float, error_type: str) -> None:
        """Record failed operation execution - legacy compatibility."""
        self._update_legacy_metrics_on_failure(error_type)
        # State transitions are handled by unified breaker
        
    def _handle_failure_state_transition(self) -> None:
        """Handle state transitions - delegated to unified breaker."""
        # State transitions are handled by unified breaker
        pass
                
    def _transition_to_open(self) -> None:
        """Transition to open state - delegated to unified breaker."""
        # Transitions are handled by unified breaker
        pass
        
    def _transition_to_half_open(self) -> None:
        """Transition to half-open state - delegated to unified breaker."""
        # Transitions are handled by unified breaker
        pass
        
    def _transition_to_closed(self) -> None:
        """Transition to closed state - delegated to unified breaker."""
        # Transitions are handled by unified breaker
        pass
        
    def get_metrics(self) -> CircuitMetrics:
        """Get current circuit breaker metrics - combines legacy and unified metrics."""
        unified_status = self._unified_breaker.get_status()
        unified_metrics = unified_status.get('metrics', {})
        
        # Update legacy metrics with unified data
        self.metrics.total_calls = max(self.metrics.total_calls, unified_metrics.get('total_calls', 0))
        self.metrics.successful_calls = max(self.metrics.successful_calls, unified_metrics.get('successful_calls', 0))
        self.metrics.failed_calls = max(self.metrics.failed_calls, unified_metrics.get('failed_calls', 0))
        self.metrics.rejected_calls = max(self.metrics.rejected_calls, unified_metrics.get('rejected_calls', 0))
        self.metrics.state_changes = unified_metrics.get('state_changes', 0)
        
        return self.metrics
        
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status - delegates to unified breaker with legacy format."""
        unified_status = self._unified_breaker.get_status()
        
        return {
            'name': self.config.name,
            'state': self.state.value,
            'is_healthy': self.state == CircuitState.CLOSED,
            'consecutive_failures': self._consecutive_failures,
            'consecutive_successes': self._consecutive_successes,
            'total_calls': self.metrics.total_calls,
            'successful_calls': self.metrics.successful_calls,
            'failed_calls': self.metrics.failed_calls,
            'rejected_calls': self.metrics.rejected_calls,
            'unified_status': unified_status  # Include unified status for debugging
        }
        
    async def reset(self) -> None:
        """Reset circuit breaker to initial state - delegates to unified breaker."""
        await self._unified_breaker.reset()
        
        # Reset legacy compatibility properties
        logger.info(f"Resetting circuit breaker '{self.config.name}'")
        self.metrics = CircuitMetrics()
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self.last_failure_time = None
        self.last_success_time = None
        
    def reset_sync(self) -> None:
        """Synchronous reset for backward compatibility."""
        try:
            # Try to get the current event loop
            loop = asyncio.get_running_loop()
            asyncio.create_task(self.reset())
        except RuntimeError:
            # No event loop running, create a new one
            asyncio.run(self.reset())
        
    # Compatibility properties - delegate to unified breaker
    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self._unified_breaker.is_open
        
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed."""
        return self._unified_breaker.is_closed
        
    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open."""
        return self._unified_breaker.is_half_open
        
    def record_success(self) -> None:
        """Record success for compatibility with legacy code - delegates to unified breaker."""
        self._unified_breaker.record_success()
        self._update_legacy_metrics_on_success()
        
    def record_failure(self, error_type: str = "generic_error") -> None:
        """Record failure for compatibility with legacy code - delegates to unified breaker."""
        self._unified_breaker.record_failure(error_type)
        self._update_legacy_metrics_on_failure(error_type)