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
from .connection import ConnectionInfo
from .error_types import WebSocketErrorInfo as WebSocketError, ErrorSeverity

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
        if strategies is None:
            strategies = [
                RecoveryStrategy.EXPONENTIAL_BACKOFF,
                RecoveryStrategy.STATE_SYNC
            ]
        
        # Create recovery context
        context = RecoveryContext(
            connection_id=connection_id,
            user_id=user_id,
            error=error,
            strategies=strategies,
            state_snapshot=self.state_snapshots.get(connection_id)
        )
        
        # Store active recovery
        self.active_recoveries[connection_id] = context
        
        logger.info(f"Starting recovery for connection {connection_id}")
        
        # Execute recovery strategies
        success = await self._execute_recovery_strategies(context)
        
        # Clean up if recovery completed
        if success or context.attempt_count >= context.max_attempts:
            self.active_recoveries.pop(connection_id, None)
        
        return success
    
    async def _execute_recovery_strategies(self, context: RecoveryContext) -> bool:
        """Execute recovery strategies in sequence."""
        for strategy in context.strategies:
            try:
                handler = self.recovery_handlers.get(strategy)
                if handler:
                    success = await handler(context)
                    if success:
                        logger.info(f"Recovery successful using {strategy}")
                        return True
                else:
                    logger.warning(f"No handler for recovery strategy: {strategy}")
            except Exception as e:
                logger.error(f"Recovery strategy {strategy} failed: {e}")
                continue
        
        logger.warning(f"All recovery strategies failed for {context.connection_id}")
        return False
    
    async def _immediate_recovery(self, context: RecoveryContext) -> bool:
        """Attempt immediate recovery."""
        # For immediate recovery, we just mark as ready to reconnect
        context.attempt_count += 1
        context.last_attempt = time.time()
        return True
    
    async def _exponential_backoff_recovery(self, context: RecoveryContext) -> bool:
        """Implement exponential backoff recovery."""
        current_time = time.time()
        
        # Check if we need to wait
        if context.last_attempt:
            elapsed = current_time - context.last_attempt
            if elapsed < context.backoff_delay:
                # Still in backoff period
                await asyncio.sleep(context.backoff_delay - elapsed)
        
        # Update attempt tracking
        context.attempt_count += 1
        context.last_attempt = time.time()
        context.backoff_delay = min(context.backoff_delay * 2, 60.0)  # Max 60s
        
        return context.attempt_count <= context.max_attempts
    
    async def _circuit_breaker_recovery(self, context: RecoveryContext) -> bool:
        """Implement circuit breaker pattern for recovery."""
        connection_id = context.connection_id
        
        # Check connection health
        health = self.connection_health.get(connection_id, 1.0)
        
        # If health is too low, don't attempt recovery
        if health < 0.3:  # 30% health threshold
            logger.warning(f"Connection {connection_id} health too low: {health}")
            return False
        
        # Update health based on error severity
        if context.error.severity == ErrorSeverity.CRITICAL:
            health *= 0.5
        elif context.error.severity == ErrorSeverity.HIGH:
            health *= 0.7
        else:
            health *= 0.9
        
        self.connection_health[connection_id] = health
        return health > 0.1  # Minimum viable threshold
    
    async def _state_sync_recovery(self, context: RecoveryContext) -> bool:
        """Implement state synchronization recovery."""
        if not context.state_snapshot:
            logger.info("No state snapshot available for recovery")
            return True  # Not a failure, just no state to recover
        
        try:
            # In a real implementation, this would restore the agent state
            # For now, we'll just log that state sync is available
            logger.info(f"State snapshot available for recovery: "
                       f"step_count={context.state_snapshot.step_count}")
            return True
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
    
    def get_recovery_status(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get recovery status for a connection."""
        context = self.active_recoveries.get(connection_id)
        if not context:
            return None
        
        return {
            "connection_id": context.connection_id,
            "attempt_count": context.attempt_count,
            "max_attempts": context.max_attempts,
            "last_attempt": context.last_attempt,
            "backoff_delay": context.backoff_delay,
            "strategies": [s.value for s in context.strategies],
            "has_state_snapshot": context.state_snapshot is not None
        }
    
    def register_recovery_handler(
        self,
        strategy: RecoveryStrategy,
        handler: Callable[[RecoveryContext], Awaitable[bool]]
    ) -> None:
        """Register a custom recovery handler."""
        self.recovery_handlers[strategy] = handler