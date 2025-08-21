"""WebSocket connection recovery and state restoration.

Provides recovery mechanisms for WebSocket connections with state persistence
and automatic reconnection handling.
"""

from typing import Dict, Any, Optional, List, Callable, Awaitable
import asyncio
import time
from enum import Enum
from dataclasses import dataclass, field

from app.logging_config import central_logger
from app.agents.state import DeepAgentState
from app.schemas.registry import WebSocketMessage
from netra_backend.app.connection import ConnectionInfo
from netra_backend.app.error_types import WebSocketErrorInfo as WebSocketError, ErrorSeverity

logger = central_logger.get_logger(__name__)


class RecoveryStrategy(str, Enum):
    """Different recovery strategies for WebSocket connections."""
    IMMEDIATE = "immediate"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    CIRCUIT_BREAKER = "circuit_breaker"
    STATE_SYNC = "state_sync"


@dataclass
class RecoveryContext:
    """Context for a recovery operation."""
    connection_id: str
    user_id: str
    error: WebSocketError
    attempt_count: int = 0
    last_attempt: Optional[float] = None
    backoff_delay: float = 1.0
    max_attempts: int = 5
    strategies: List[RecoveryStrategy] = field(default_factory=list)
    state_snapshot: Optional[DeepAgentState] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class WebSocketRecoveryManager:
    """Manages WebSocket connection recovery and state restoration."""
    
    def __init__(self):
        """Initialize recovery manager."""
        self.active_recoveries: Dict[str, RecoveryContext] = {}
        self.recovery_handlers: Dict[RecoveryStrategy, Callable] = {}
        self.state_snapshots: Dict[str, DeepAgentState] = {}
        self.connection_health: Dict[str, float] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default recovery strategy handlers."""
        self.recovery_handlers = {
            RecoveryStrategy.IMMEDIATE: self._immediate_recovery,
            RecoveryStrategy.EXPONENTIAL_BACKOFF: self._exponential_backoff_recovery,
            RecoveryStrategy.CIRCUIT_BREAKER: self._circuit_breaker_recovery,
            RecoveryStrategy.STATE_SYNC: self._state_sync_recovery
        }
    
    async def initiate_recovery(
        self,
        connection_id: str,
        user_id: str,
        error: WebSocketError,
        strategies: Optional[List[RecoveryStrategy]] = None
    ) -> bool:
        """Initiate recovery for a failed connection."""
        strategies = self._prepare_recovery_strategies(strategies)
        context = self._create_recovery_context(connection_id, user_id, error, strategies)
        return await self._execute_recovery_process(connection_id, context)
    
    def _prepare_recovery_strategies(self, strategies: Optional[List[RecoveryStrategy]]) -> List[RecoveryStrategy]:
        """Prepare recovery strategies with defaults if needed."""
        if strategies is None:
            return [RecoveryStrategy.EXPONENTIAL_BACKOFF, RecoveryStrategy.STATE_SYNC]
        return strategies
    
    def _create_recovery_context(self, connection_id: str, user_id: str, 
                               error: WebSocketError, strategies: List[RecoveryStrategy]) -> RecoveryContext:
        """Create recovery context for the connection."""
        return RecoveryContext(
            connection_id=connection_id,
            user_id=user_id,
            error=error,
            strategies=strategies,
            state_snapshot=self.state_snapshots.get(connection_id)
        )
    
    async def _execute_recovery_process(self, connection_id: str, context: RecoveryContext) -> bool:
        """Execute the recovery process and handle cleanup."""
        self.active_recoveries[connection_id] = context
        logger.info(f"Starting recovery for connection {connection_id}")
        success = await self._execute_recovery_strategies(context)
        self._cleanup_recovery_if_needed(connection_id, context, success)
        return success
    
    def _cleanup_recovery_if_needed(self, connection_id: str, context: RecoveryContext, success: bool) -> None:
        """Clean up recovery context if recovery completed."""
        if success or context.attempt_count >= context.max_attempts:
            self.active_recoveries.pop(connection_id, None)
    
    async def _try_single_recovery_strategy(self, strategy: RecoveryStrategy, context: RecoveryContext) -> Optional[bool]:
        """Try a single recovery strategy and return success status or None if no handler."""
        handler = self.recovery_handlers.get(strategy)
        if not handler:
            logger.warning(f"No handler for recovery strategy: {strategy}")
            return None
        return await self._execute_handler_with_logging(handler, strategy, context)
    
    async def _execute_handler_with_logging(self, handler: Callable, strategy: RecoveryStrategy, context: RecoveryContext) -> bool:
        """Execute recovery handler and log success if applicable."""
        success = await handler(context)
        if success:
            logger.info(f"Recovery successful using {strategy}")
        return success

    def _log_all_strategies_failed(self, connection_id: str) -> None:
        """Log that all recovery strategies have failed."""
        logger.warning(f"All recovery strategies failed for {connection_id}")

    async def _execute_recovery_strategies(self, context: RecoveryContext) -> bool:
        """Execute recovery strategies in sequence."""
        for strategy in context.strategies:
            success = await self._try_strategy_with_error_handling(strategy, context)
            if success:
                return True
        
        self._log_all_strategies_failed(context.connection_id)
        return False
    
    async def _try_strategy_with_error_handling(self, strategy: RecoveryStrategy, context: RecoveryContext) -> bool:
        """Try a single recovery strategy with error handling."""
        try:
            success = await self._try_single_recovery_strategy(strategy, context)
            return bool(success)
        except Exception as e:
            logger.error(f"Recovery strategy {strategy} failed: {e}")
            return False
    
    async def _immediate_recovery(self, context: RecoveryContext) -> bool:
        """Attempt immediate recovery."""
        # For immediate recovery, we just mark as ready to reconnect
        context.attempt_count += 1
        context.last_attempt = time.time()
        return True
    
    async def _handle_backoff_delay(self, context: RecoveryContext) -> None:
        """Handle exponential backoff delay if needed."""
        if not context.last_attempt:
            return
        
        current_time = time.time()
        elapsed = current_time - context.last_attempt
        if elapsed < context.backoff_delay:
            await asyncio.sleep(context.backoff_delay - elapsed)

    def _update_backoff_attempt(self, context: RecoveryContext) -> None:
        """Update attempt count and backoff delay."""
        context.attempt_count += 1
        context.last_attempt = time.time()
        context.backoff_delay = min(context.backoff_delay * 2, 60.0)  # Max 60s

    async def _exponential_backoff_recovery(self, context: RecoveryContext) -> bool:
        """Implement exponential backoff recovery."""
        await self._handle_backoff_delay(context)
        self._update_backoff_attempt(context)
        return context.attempt_count <= context.max_attempts
    
    def _get_connection_health(self, connection_id: str) -> float:
        """Get current health for connection."""
        return self.connection_health.get(connection_id, 1.0)
    
    def _is_health_sufficient_for_recovery(self, health: float, connection_id: str) -> bool:
        """Check if health is above threshold for recovery attempt."""
        if health < 0.3:  # 30% health threshold
            logger.warning(f"Connection {connection_id} health too low: {health}")
            return False
        return True
    
    def _calculate_new_health_from_severity(self, health: float, severity: ErrorSeverity) -> float:
        """Calculate new health value based on error severity."""
        if severity == ErrorSeverity.CRITICAL:
            return health * 0.5
        elif severity == ErrorSeverity.HIGH:
            return health * 0.7
        else:
            return health * 0.9
    
    def _update_and_validate_health(self, connection_id: str, new_health: float) -> bool:
        """Update stored health and validate against minimum threshold."""
        self.connection_health[connection_id] = new_health
        return new_health > 0.1  # Minimum viable threshold
    
    async def _circuit_breaker_recovery(self, context: RecoveryContext) -> bool:
        """Implement circuit breaker pattern for recovery."""
        connection_id = context.connection_id
        health = self._get_connection_health(connection_id)
        
        if not self._is_health_sufficient_for_recovery(health, connection_id):
            return False
        
        new_health = self._calculate_new_health_from_severity(health, context.error.severity)
        return self._update_and_validate_health(connection_id, new_health)
    
    def _validate_state_snapshot(self, context: RecoveryContext) -> bool:
        """Validate if state snapshot is available for recovery."""
        if not context.state_snapshot:
            logger.info("No state snapshot available for recovery")
            return False
        return True

    def _perform_state_restoration(self, context: RecoveryContext) -> bool:
        """Perform the actual state restoration process."""
        # In a real implementation, this would restore the agent state
        # For now, we'll just log that state sync is available
        logger.info(f"State snapshot available for recovery: "
                   f"step_count={context.state_snapshot.step_count}")
        return True

    async def _state_sync_recovery(self, context: RecoveryContext) -> bool:
        """Implement state synchronization recovery."""
        if not self._validate_state_snapshot(context):
            return True  # Not a failure, just no state to recover
        
        try:
            return self._perform_state_restoration(context)
        except Exception as e:
            logger.error(f"State sync recovery failed: {e}")
            return False
    
    def save_state_snapshot(self, connection_id: str, state: DeepAgentState) -> None:
        """Save state snapshot for potential recovery."""
        self.state_snapshots[connection_id] = state
        logger.debug(f"Saved state snapshot for connection {connection_id}")
    
    def clear_state_snapshot(self, connection_id: str) -> None:
        """Clear state snapshot when no longer needed."""
        self.state_snapshots.pop(connection_id, None)
        self.connection_health.pop(connection_id, None)
        self.active_recoveries.pop(connection_id, None)
    
    def _build_recovery_status_dict(self, context: RecoveryContext) -> Dict[str, Any]:
        """Build recovery status dictionary from context."""
        base_fields = self._build_context_fields(context)
        strategy_fields = self._build_strategy_fields(context)
        return {**base_fields, **strategy_fields}
    
    def _build_context_fields(self, context: RecoveryContext) -> Dict[str, Any]:
        """Build context-related fields for recovery status."""
        return {
            "connection_id": context.connection_id,
            "attempt_count": context.attempt_count,
            "max_attempts": context.max_attempts,
            "last_attempt": context.last_attempt,
            "backoff_delay": context.backoff_delay
        }
    
    def _build_strategy_fields(self, context: RecoveryContext) -> Dict[str, Any]:
        """Build strategy-related fields for recovery status."""
        return {
            "strategies": [s.value for s in context.strategies],
            "has_state_snapshot": context.state_snapshot is not None
        }

    def get_recovery_status(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get recovery status for a connection."""
        context = self.active_recoveries.get(connection_id)
        if not context:
            return None
        return self._build_recovery_status_dict(context)
    
    def register_recovery_handler(
        self,
        strategy: RecoveryStrategy,
        handler: Callable[[RecoveryContext], Awaitable[bool]]
    ) -> None:
        """Register a custom recovery handler."""
        self.recovery_handlers[strategy] = handler